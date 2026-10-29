"""Score pipeline results against ground truth.

Field correctness is exact after light normalization: text is compared
case-insensitively ignoring commas, periods and extra spaces; amounts to the
cent; dates as ISO strings. A null predicted for a null truth is correct (the
model correctly said the field is absent).

Error accounting, per wrong field:
- caught (document level): the document went to review, so a person sees it;
- caught (field level): the wrong field itself carries a flag;
- missed: the document was auto-accepted. These are the errors that matter.
"""

from __future__ import annotations

import difflib
import re
import statistics
from dataclasses import asdict, dataclass
from typing import Any

from evals.dataset import Case
from intake.fields import ROW_KINDS
from intake.pipeline import IntakeResult
from intake.routing import AUTO_ACCEPT
from intake.schemas import ITEM_KEY

BINS = [(0.0, 0.5), (0.5, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 0.95), (0.95, 0.98), (0.98, 1.01)]
SWEEP = [0.5, 0.7, 0.8, 0.85, 0.9, 0.95, 0.97]


def _norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[.,]", "", s)).strip().casefold()


def values_equal(kind: str, truth: Any, pred: Any) -> bool:
    if truth is None or pred is None:
        return truth is None and pred is None
    if kind in ("money", "number"):
        return abs(float(truth) - float(pred)) < 0.005
    if kind == "int":
        return int(truth) == int(pred)
    return _norm_text(str(truth)) == _norm_text(str(pred))


@dataclass
class FieldScore:
    doc_id: str
    doc_type: str
    variant: str
    path: str
    kind: str
    truth: Any
    predicted: Any
    correct: bool
    confidence: float | None
    flags: list[str]
    citation: str | None
    doc_route: str

    @property
    def flagged(self) -> bool:
        return bool(self.flags)


ROW_KEY = {"line_items": "description", "claims": "claim_number"}


def align_rows(truth_keys: list[str], pred_keys: list[str]) -> list[tuple[int | None, int | None]]:
    """Pair truth rows with predicted rows (difflib on the row key: description or claim
    number). Without this, one dropped row would shift every later row and turn a single
    mistake into dozens of "wrong" fields. Unpaired rows are (i, None) missing or
    (None, j) extra."""
    norm = [_norm_text(k) for k in truth_keys], [_norm_text(k) for k in pred_keys]
    pairs: list[tuple[int | None, int | None]] = []
    sm = difflib.SequenceMatcher(a=norm[0], b=norm[1], autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            pairs += list(zip(range(i1, i2), range(j1, j2), strict=True))
        else:  # replace / delete / insert: pair positionally, leftovers are missing or extra
            ti, pj = list(range(i1, i2)), list(range(j1, j2))
            n = min(len(ti), len(pj))
            pairs += list(zip(ti[:n], pj[:n], strict=True))
            pairs += [(i, None) for i in ti[n:]] + [(None, j) for j in pj[n:]]
    return pairs


def score_document(case: Case, result: IntakeResult) -> list[FieldScore]:
    truth = case.fields()
    pred = {f.path: f for f in result.fields}
    key = ITEM_KEY[case.doc_type]
    # map truth path -> predicted path
    mapping: dict[str, str | None] = {p: (p if p in pred else None) for p in truth if "[" not in p}
    extra: list[str] = []
    if key:
        col = ROW_KEY[key]
        t_rows = case.truth[key]
        p_rows = sorted({f.row for f in result.fields if f.row is not None})
        p_keys = [str(pred[f"{key}[{j}].{col}"].value) for j in p_rows]
        for i, j in align_rows([str(r[col]) for r in t_rows], p_keys):
            for c in ROW_KINDS[key]:
                if i is None:
                    extra.append(f"{key}[{p_rows[j]}].{c}")
                else:
                    mapping[f"{key}[{i}].{c}"] = None if j is None else f"{key}[{p_rows[j]}].{c}"
    out = []
    for path, (kind, tv) in truth.items():
        f = pred.get(mapping.get(path) or "")
        pv = f.value if f else None
        out.append(FieldScore(case.doc_id, case.doc_type, case.truth["variant"], path, kind, tv,
                              pv, f is not None and values_equal(kind, tv, pv) or
                              (f is None and tv is None and "[" not in path),
                              f.confidence if f else None, list(f.flags) if f else [],
                              f.citation if f else None, result.route))
    for path in extra:  # an invented row is wrong in every column
        f = pred[path]
        out.append(FieldScore(case.doc_id, case.doc_type, case.truth["variant"], f"extra:{path}",
                              f.kind, None, f.value, False, f.confidence, list(f.flags),
                              f.citation, result.route))
    return out


def _acc(rows: list[FieldScore]) -> dict[str, Any]:
    n = len(rows)
    c = sum(r.correct for r in rows)
    return {"fields": n, "correct": c, "accuracy": round(c / n, 4) if n else None}


def _pct(values: list[float], q: float) -> float | None:
    if not values:
        return None
    s = sorted(values)
    return round(s[min(len(s) - 1, int(round(q * (len(s) - 1))))], 1)


def summarize(cases: list[Case], results: list[IntakeResult],
              scores: list[FieldScore], threshold: float) -> dict[str, Any]:
    by_doc = {r.document_id: r for r in results}
    wrong = [s for s in scores if not s.correct]

    doc_rows = []
    for c in cases:
        r = by_doc[c.doc_id]
        s = [x for x in scores if x.doc_id == c.doc_id]
        doc_rows.append({
            "doc_id": c.doc_id, "doc_type": c.doc_type, "variant": c.truth["variant"],
            "expected_review": c.truth["expected_review"],
            "expected_reason": c.truth["expected_reason"], "route": r.route,
            "reason_codes": sorted({x.code for x in r.reasons}),
            "reasons": [x.detail for x in r.reasons][:8],
            "fields": len(s), "wrong_fields": sum(not x.correct for x in s),
            "attempts": r.attempts, "input_tokens": r.input_tokens,
            "output_tokens": r.output_tokens, "cost_usd": r.cost_usd,
            "latency_ms": r.latency_ms, "pii_masked": r.pii_masked})

    expected = [d for d in doc_rows if d["expected_review"]]
    not_expected = [d for d in doc_rows if not d["expected_review"]]

    calib = []
    with_conf = [s for s in scores if s.confidence is not None]
    for lo, hi in BINS:
        b = [s for s in with_conf if lo <= s.confidence < hi]
        calib.append({"bin": f"[{lo:.2f}, {min(hi, 1.0):.2f}{')' if hi < 1.01 else ']'}",
                      "fields": len(b),
                      "mean_confidence": round(statistics.mean(s.confidence for s in b), 3)
                      if b else None,
                      "observed_accuracy": round(sum(s.correct for s in b) / len(b), 3)
                      if b else None})

    # what-if: same run, different confidence thresholds (other reasons unchanged)
    sweep = []
    for t in SWEEP:
        auto_docs = set()
        for r in results:
            other = [x for x in r.reasons if x.code != "low_confidence"]
            if not other and all(f.confidence >= t for f in r.fields):
                auto_docs.add(r.document_id)
        auto_fields = [s for s in scores if s.doc_id in auto_docs]
        sweep.append({"threshold": t, "auto_accepted_docs": len(auto_docs),
                      "auto_accepted_fields": len(auto_fields),
                      "missed_errors": sum(not s.correct for s in auto_fields)})

    costs = [r.cost_usd for r in results if r.cost_usd is not None]
    lat = [r.latency_ms for r in results]
    return {
        "documents": len(results),
        "fields": len(scores),
        "threshold": threshold,
        "accuracy_overall": _acc(scores),
        "accuracy_by_doc_type": {t: _acc([s for s in scores if s.doc_type == t])
                                 for t in sorted({c.doc_type for c in cases})},
        "accuracy_by_variant": {v: _acc([s for s in scores if s.variant == v])
                                for v in sorted({c.truth["variant"] for c in cases})},
        "accuracy_by_route": {"auto_accept": _acc([s for s in scores
                                                   if s.doc_route == AUTO_ACCEPT]),
                              "needs_review": _acc([s for s in scores
                                                    if s.doc_route != AUTO_ACCEPT])},
        "accuracy_by_field_flag": {"flagged": _acc([s for s in scores if s.flagged]),
                                   "not_flagged": _acc([s for s in scores if not s.flagged])},
        "routing": {
            "auto_accept": sum(d["route"] == AUTO_ACCEPT for d in doc_rows),
            "needs_review": sum(d["route"] != AUTO_ACCEPT for d in doc_rows),
            "hard_cases_expected_review": len(expected),
            "hard_cases_sent_to_review": sum(d["route"] != AUTO_ACCEPT for d in expected),
            "hard_cases_with_expected_reason": sum(
                d["expected_reason"] in d["reason_codes"] for d in expected),
            "clean_docs": len(not_expected),
            "clean_docs_sent_to_review": sum(d["route"] != AUTO_ACCEPT for d in not_expected),
            # reviewed although nothing was wrong and no hard case was planted: pure reviewer cost
            "false_alarms": sum(d["route"] != AUTO_ACCEPT and d["wrong_fields"] == 0
                                for d in not_expected),
        },
        "errors": {
            "wrong_fields": len(wrong),
            "caught_doc_level": sum(s.doc_route != AUTO_ACCEPT for s in wrong),
            "caught_field_level": sum(s.flagged for s in wrong),
            # a field the model never produced (dropped row, failed extraction) cannot carry a
            # flag; it is only visible through the document's route and the sum rules
            "wrong_produced": sum(s.confidence is not None for s in wrong),
            "not_produced": sum(s.confidence is None for s in wrong),
            "missed_in_auto_accepted_docs": sum(s.doc_route == AUTO_ACCEPT for s in wrong),
            "missed": [asdict(s) for s in wrong if s.doc_route == AUTO_ACCEPT],
            "all_wrong": [asdict(s) for s in wrong],
        },
        "calibration": calib,
        "threshold_sweep": sweep,
        "cost": {"total_usd": round(sum(costs), 4) if costs else None,
                 "mean_usd_per_doc": round(statistics.mean(costs), 5) if costs else None,
                 "input_tokens": sum(r.input_tokens for r in results),
                 "output_tokens": sum(r.output_tokens for r in results)},
        "latency_ms": {"mean": round(statistics.mean(lat), 1) if lat else None,
                       "p50": _pct(lat, 0.5), "p95": _pct(lat, 0.95),
                       "max": round(max(lat), 1) if lat else None},
        "retries": sum(r.attempts > 1 for r in results),
        "extraction_failures": sum(any(x.code in ("extraction_invalid", "model_error")
                                       for x in r.reasons) for r in results),
        "pii_strings_masked_by_code": sum(r.pii_masked for r in results),
        "documents_detail": doc_rows,
    }
