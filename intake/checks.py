"""Deterministic checks. None of them trust the model.

1. Citation verification: the cited text must appear on the cited page of the
   document's own text layer, and the extracted value must appear inside the
   cited text. A value the model invented, or read from the wrong place,
   usually fails one of the two.
2. Business rules: arithmetic (line items, totals, claim amounts), tax rates
   on a W-2, date sanity (policy period order, losses inside the period), and
   formats. Each rule names the fields it implicates, so routing can flag them.

Amounts are compared in integer cents to avoid float drift.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import date

from pydantic import BaseModel

from intake.documents import LoadedDocument, squash
from intake.fields import FieldView
from intake.schemas import PII_FIELDS

# ---------------------------------------------------------------- citations

VERIFIED = "verified"
UNVERIFIABLE = "unverifiable"  # no text layer (scan); value-in-citation still checked
ABSENT = "absent"  # value is null, nothing to cite
FAILURES = ("missing_citation", "not_found", "wrong_page", "value_not_in_citation")


def value_renderings(kind: str, value) -> list[str]:
    """Ways a value is commonly printed. The value must match one of them inside its citation."""
    if value is None:
        return []
    if kind == "money" or kind == "number":
        x = float(value)
        forms = {f"{x:,.2f}", f"{x:.2f}", f"({abs(x):,.2f})"}
        if x == int(x):
            forms |= {f"{int(x):,}", str(int(x))}
        else:
            forms |= {f"{x:g}"}
        return sorted(forms)
    if kind == "int":
        return [str(value), f"{int(value):,}"]
    if kind == "date":
        d = date.fromisoformat(value)
        return [d.isoformat(), d.strftime("%m/%d/%Y"), f"{d.month}/{d.day}/{d.year}",
                d.strftime("%m/%d/%y"), d.strftime("%m-%d-%Y"), d.strftime("%B %-d, %Y"),
                d.strftime("%b %-d, %Y"), d.strftime("%-d %B %Y"), d.strftime("%b. %-d, %Y")]
    return [str(value)]


def _ssn_on_page(page_text: str, masked: str) -> bool:
    last4 = masked[-4:]
    return re.search(rf"\b\d{{3}}[- ]?\d{{2}}[- ]?{last4}\b", page_text) is not None


def check_citation(f: FieldView, doc: LoadedDocument, pii: bool = False) -> str:
    if f.value is None:
        return ABSENT
    if not f.source_text or not f.source_text.strip():
        return "missing_citation"
    cited = squash(f.source_text)
    if not pii and not any(squash(r) in cited for r in value_renderings(f.kind, f.value)):
        return "value_not_in_citation"
    if pii and squash(str(f.value)) not in cited:
        return "value_not_in_citation"
    if not doc.has_text_layer:
        return UNVERIFIABLE
    texts = doc.page_texts or []
    page_ok = f.page is not None and 1 <= f.page <= len(texts)

    def on(i: int) -> bool:
        return _ssn_on_page(texts[i], str(f.value)) if pii else cited in squash(texts[i])

    if page_ok and on(f.page - 1):
        return VERIFIED
    if any(on(i) for i in range(len(texts))):
        return "wrong_page"
    return "not_found"


def verify_citations(doc_type: str, fields: list[FieldView], doc: LoadedDocument) -> None:
    pii = PII_FIELDS.get(doc_type, ())
    for f in fields:
        f.citation = check_citation(f, doc, pii=f.path in pii)


# ---------------------------------------------------------------- rules

@dataclass
class RuleResult:
    rule: str
    status: str  # pass | fail | skipped
    detail: str = ""
    fields: list[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


def cents(x: float) -> int:
    return round(x * 100)


def _v(x) -> object:
    """Value of a Cited[...] field (None when absent)."""
    return x.value


def _rule(results: list[RuleResult], name: str, inputs: list, ok: Callable[[], bool],
          detail: Callable[[], str], fields: list[str]) -> None:
    if any(i is None for i in inputs):
        results.append(RuleResult(name, "skipped", "an input is missing"))
    elif ok():
        results.append(RuleResult(name, "pass"))
    else:
        results.append(RuleResult(name, "fail", detail(), fields))


def invoice_rules(x: BaseModel) -> list[RuleResult]:
    r: list[RuleResult] = []
    items = x.line_items
    for i, it in enumerate(items):
        _rule(r, f"line_items[{i}]_qty_times_price", [it.quantity],
              lambda it=it: abs(cents(it.quantity * it.unit_price) - cents(it.amount)) <= 1,
              lambda it=it: f"{it.quantity} x {it.unit_price:.2f} != {it.amount:.2f}",
              [f"line_items[{i}].amount", f"line_items[{i}].quantity",
               f"line_items[{i}].unit_price"])
    sub, tax, total = _v(x.subtotal), _v(x.tax), _v(x.total)
    line_sum = sum(cents(it.amount) for it in items)
    _rule(r, "line_items_sum_to_subtotal", [sub] if items else [None],
          lambda: line_sum == cents(sub),
          lambda: f"line items sum to {line_sum / 100:.2f}, subtotal is {sub:.2f}",
          ["subtotal"] + [f"line_items[{i}].amount" for i in range(len(items))])
    _rule(r, "subtotal_plus_tax_equals_total", [sub, tax, total],
          lambda: abs(cents(sub) + cents(tax) - cents(total)) <= 1,
          lambda: f"{sub:.2f} + {tax:.2f} = {(cents(sub) + cents(tax)) / 100:.2f}, "
                  f"total is {total:.2f}",
          ["subtotal", "tax", "total"])
    inv, due = _v(x.invoice_date), _v(x.due_date)
    _rule(r, "due_date_not_before_invoice_date", [inv, due], lambda: due >= inv,
          lambda: f"due {due} is before invoice date {inv}", ["due_date", "invoice_date"])
    terms = _v(x.payment_terms)
    m = re.search(r"net\s*(\d+)", terms or "", re.I)
    _rule(r, "net_terms_match_due_date", [inv, due, m],
          lambda: (due - inv).days == int(m.group(1)),
          lambda: f"terms say {terms} but due date is {(due - inv).days} days after invoice",
          ["payment_terms", "due_date", "invoice_date"])
    return r


SS_RATE, MEDICARE_RATE = 0.062, 0.0145
SS_WAGE_BASE = {2024: 168_600, 2025: 176_100}  # SSA published wage bases
ADDITIONAL_MEDICARE_THRESHOLD = 200_000  # above this the 0.9% surtax makes box 6 vary


def w2_rules(x: BaseModel) -> list[RuleResult]:
    r: list[RuleResult] = []
    year = _v(x.tax_year)
    w1, w2_, w3, w4, w5, w6 = (_v(x.wages), _v(x.federal_income_tax_withheld),
                               _v(x.social_security_wages), _v(x.social_security_tax_withheld),
                               _v(x.medicare_wages), _v(x.medicare_tax_withheld))
    _rule(r, "social_security_tax_is_6.2_percent", [w3, w4],
          lambda: abs(cents(w4) - cents(w3 * SS_RATE)) <= 100,
          lambda: f"box 4 is {w4:.2f}; 6.2% of box 3 is {w3 * SS_RATE:.2f}",
          ["social_security_tax_withheld", "social_security_wages"])
    if w5 is not None and w5 > ADDITIONAL_MEDICARE_THRESHOLD:
        r.append(RuleResult("medicare_tax_is_1.45_percent", "skipped",
                            "wages above the additional Medicare tax threshold"))
    else:
        _rule(r, "medicare_tax_is_1.45_percent", [w5, w6],
              lambda: abs(cents(w6) - cents(w5 * MEDICARE_RATE)) <= 100,
              lambda: f"box 6 is {w6:.2f}; 1.45% of box 5 is {w5 * MEDICARE_RATE:.2f}",
              ["medicare_tax_withheld", "medicare_wages"])
    base = SS_WAGE_BASE.get(year) if year else None
    _rule(r, "social_security_wages_within_wage_base", [w3, base], lambda: w3 <= base,
          lambda: f"box 3 {w3:.2f} exceeds the {year} wage base {base:,}",
          ["social_security_wages"])
    _rule(r, "withholding_below_wages", [w1, w2_], lambda: w2_ < w1,
          lambda: f"box 2 {w2_:.2f} is not below box 1 {w1:.2f}",
          ["federal_income_tax_withheld", "wages"])
    ein = _v(x.employer_ein)
    _rule(r, "ein_format", [ein], lambda: re.fullmatch(r"\d{2}-\d{7}", ein) is not None,
          lambda: "EIN is not NN-NNNNNNN", ["employer_ein"])
    _rule(r, "tax_year_plausible", [year], lambda: 2000 <= year <= date.today().year,
          lambda: f"tax year {year} is implausible", ["tax_year"])
    return r


def loss_run_rules(x: BaseModel) -> list[RuleResult]:
    r: list[RuleResult] = []
    claims = x.claims
    for i, c in enumerate(claims):
        _rule(r, f"claims[{i}]_paid_plus_reserve_equals_incurred", [c.paid],
              lambda c=c: cents(c.paid) + cents(c.reserved) == cents(c.incurred),
              lambda c=c: f"{c.paid:.2f} + {c.reserved:.2f} != {c.incurred:.2f}",
              [f"claims[{i}].paid", f"claims[{i}].reserved", f"claims[{i}].incurred"])
        _rule(r, f"claims[{i}]_closed_has_no_reserve", [c.status],
              lambda c=c: c.status != "closed" or cents(c.reserved) == 0,
              lambda c=c: f"closed claim carries a reserve of {c.reserved:.2f}",
              [f"claims[{i}].status", f"claims[{i}].reserved"])
    for col, total_name in (("paid", "total_paid"), ("reserved", "total_reserved"),
                            ("incurred", "total_incurred")):
        total = _v(getattr(x, total_name))
        s = sum(cents(getattr(c, col)) for c in claims)
        _rule(r, f"claims_{col}_sum_to_{total_name}", [total], lambda s=s, t=total: s == cents(t),
              lambda s=s, t=total, col=col: f"claim {col} sums to {s / 100:,.2f}, "
                                            f"printed total is {t:,.2f}",
              [total_name] + [f"claims[{i}].{col}" for i in range(len(claims))])
    tp, tr, ti = _v(x.total_paid), _v(x.total_reserved), _v(x.total_incurred)
    _rule(r, "total_paid_plus_reserved_equals_incurred", [tp, tr, ti],
          lambda: cents(tp) + cents(tr) == cents(ti),
          lambda: f"{tp:,.2f} + {tr:,.2f} != {ti:,.2f}",
          ["total_paid", "total_reserved", "total_incurred"])
    start, end, val = _v(x.policy_period_start), _v(x.policy_period_end), _v(x.valuation_date)
    _rule(r, "policy_period_start_before_end", [start, end], lambda: start < end,
          lambda: f"policy period starts {start}, ends {end}",
          ["policy_period_start", "policy_period_end"])
    _rule(r, "valuation_not_before_policy_start", [start, val], lambda: val >= start,
          lambda: f"valuation date {val} is before policy start {start}", ["valuation_date"])
    if start and end:
        outside = [i for i, c in enumerate(claims) if not start <= c.date_of_loss <= end]
        r.append(RuleResult(
            "losses_inside_policy_period", "fail" if outside else "pass",
            f"claims {outside} have a date of loss outside {start}..{end}" if outside else "",
            [f"claims[{i}].date_of_loss" for i in outside]))
    else:
        r.append(RuleResult("losses_inside_policy_period", "skipped", "policy period missing"))
    return r


RULES = {"invoice": invoice_rules, "w2": w2_rules, "loss_run": loss_run_rules}


def run_rules(doc_type: str, extraction: BaseModel) -> list[RuleResult]:
    return RULES[doc_type](extraction)
