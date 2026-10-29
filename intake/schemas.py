"""Extraction schemas, one pydantic model per document type.

Every scalar field is a `Cited[...]`: the value plus the model's confidence and
a citation (page number and the exact text the value was read from). Line items
and claims carry one confidence and one citation per row.

The same models do two jobs:
- `output_json_schema(doc_type)` turns them into the JSON Schema sent to the
  API as a structured-output format, so the response always has this shape;
- `parse_extraction(...)` validates the response with pydantic, which also
  enforces what the API schema cannot express (confidence in [0, 1], ISO
  dates, masked SSN, page numbers that exist). A failure here triggers the
  single retry in intake/extract.py.
"""

from __future__ import annotations

import copy
import json
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

DocType = Literal["invoice", "w2", "loss_run"]
DOC_TYPES: tuple[str, ...] = ("invoice", "w2", "loss_run")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _CitedBase(_Strict):
    confidence: float = Field(ge=0.0, le=1.0, description=(
        "Probability (0 to 1) that the value is exactly right. For a null value: that the field "
        "is truly not printed. Lower it when text is blurry, ambiguous or hard to locate."))
    page: int | None = Field(description="1-based page the value was read from; null if absent.")
    source_text: str | None = Field(description=(
        "Short verbatim span copied from the document that contains the value, including its "
        "label when the label is on the same line. Null if the field is absent."))


class CitedText(_CitedBase):
    value: str | None


class CitedMoney(_CitedBase):
    value: float | None = Field(description="Number without currency symbols or commas.")


class CitedDate(_CitedBase):
    value: date | None = Field(description="ISO date, YYYY-MM-DD.")


class CitedInt(_CitedBase):
    value: int | None


class _RowBase(_Strict):
    confidence: float = Field(ge=0.0, le=1.0, description="Probability the whole row is right.")
    page: int = Field(description="1-based page the row is on.")
    source_text: str = Field(description="The row copied verbatim, cells separated by spaces.")


# ---------------------------------------------------------------- invoice

class InvoiceLineItem(_RowBase):
    description: str
    quantity: float
    unit_price: float = Field(description="Negative for a discount or credit line.")
    amount: float = Field(description="Line amount; negative for a discount or credit line.")


class InvoiceExtraction(_Strict):
    vendor_name: CitedText = Field(description="Company that issued the invoice.")
    customer_name: CitedText = Field(description="Company being billed (bill to / customer).")
    invoice_number: CitedText
    invoice_date: CitedDate
    due_date: CitedDate
    payment_terms: CitedText = Field(description="For example 'Net 30', as printed.")
    po_number: CitedText = Field(description="Customer purchase order number, if printed.")
    line_items: list[InvoiceLineItem] = Field(description="Every line item, in document order.")
    subtotal: CitedMoney = Field(description="Invoice subtotal (not a per-page subtotal).")
    tax: CitedMoney
    total: CitedMoney = Field(description=(
        "Invoice total as printed (subtotal plus tax). If a deposit or payment is subtracted "
        "below it, still report the invoice total, not the remaining balance. Do not compute."))


# ---------------------------------------------------------------- W-2

class W2Extraction(_Strict):
    tax_year: CitedInt
    employer_name: CitedText
    employer_ein: CitedText = Field(description="Box b, as printed (NN-NNNNNNN).")
    employee_name: CitedText = Field(description="Box e, first and last name.")
    employee_ssn: CitedText = Field(description=(
        "Box a. Return ONLY the masked form XXX-XX-#### (last four digits), in both value and "
        "source_text. Never output the full number."))
    wages: CitedMoney = Field(description="Box 1.")
    federal_income_tax_withheld: CitedMoney = Field(description="Box 2.")
    social_security_wages: CitedMoney = Field(description="Box 3.")
    social_security_tax_withheld: CitedMoney = Field(description="Box 4.")
    medicare_wages: CitedMoney = Field(description="Box 5.")
    medicare_tax_withheld: CitedMoney = Field(description="Box 6.")

    @field_validator("employee_ssn")
    @classmethod
    def _ssn_masked(cls, v: CitedText) -> CitedText:
        from intake.pii import MASKED_SSN

        if v.value is not None and not MASKED_SSN.fullmatch(v.value):
            raise ValueError("employee_ssn.value must be masked as XXX-XX-#### (last four only)")
        return v


# ---------------------------------------------------------------- loss run

class LossRunClaim(_RowBase):
    claim_number: str
    date_of_loss: date
    status: Literal["open", "closed"]
    paid: float = Field(description=(
        "Total paid on the claim. If paid is split into categories (indemnity, expense), "
        "use the printed total paid column."))
    reserved: float = Field(description="Outstanding reserve.")
    incurred: float = Field(description="Total incurred as printed for the claim.")


class LossRunExtraction(_Strict):
    carrier_name: CitedText = Field(description="Insurance company that issued the report.")
    insured_name: CitedText = Field(description="Named insured.")
    policy_number: CitedText
    policy_period_start: CitedDate
    policy_period_end: CitedDate
    valuation_date: CitedDate = Field(description="Date the losses are valued as of.")
    claims: list[LossRunClaim] = Field(description="Every claim row on every page, in order.")
    total_paid: CitedMoney = Field(description="Printed total paid. Do not compute.")
    total_reserved: CitedMoney = Field(description="Printed total reserve. Do not compute.")
    total_incurred: CitedMoney = Field(description="Printed total incurred. Do not compute.")


MODELS: dict[str, type[_Strict]] = {
    "invoice": InvoiceExtraction, "w2": W2Extraction, "loss_run": LossRunExtraction,
}
ITEM_KEY: dict[str, str | None] = {"invoice": "line_items", "w2": None, "loss_run": "claims"}
# Business-required fields: a null value sends the document to review.
REQUIRED: dict[str, tuple[str, ...]] = {
    "invoice": ("vendor_name", "customer_name", "invoice_number", "invoice_date", "subtotal",
                "total"),
    "w2": ("tax_year", "employer_name", "employer_ein", "employee_name", "employee_ssn",
           "wages", "federal_income_tax_withheld"),
    "loss_run": ("carrier_name", "insured_name", "policy_number", "policy_period_start",
                 "policy_period_end", "total_incurred"),
}
PII_FIELDS: dict[str, tuple[str, ...]] = {"w2": ("employee_ssn",)}


# ---------------------------------------------------------------- JSON schema for the API

_UNSUPPORTED = ("title", "default", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
                "minLength", "maxLength", "minItems", "maxItems", "pattern")


def _tighten(node: Any) -> Any:
    """Structured outputs need additionalProperties false and every property required, and
    reject numeric/string constraints. Pydantic still enforces those constraints locally."""
    if isinstance(node, dict):
        out = {k: _tighten(v) for k, v in node.items() if k not in _UNSUPPORTED}
        if out.get("type") == "object" and "properties" in out:
            out["additionalProperties"] = False
            out["required"] = list(out["properties"])
        return out
    if isinstance(node, list):
        return [_tighten(v) for v in node]
    return node


def output_json_schema(doc_type: str) -> dict[str, Any]:
    return _tighten(copy.deepcopy(MODELS[doc_type].model_json_schema()))


# ---------------------------------------------------------------- parsing

class ExtractionInvalid(Exception):
    """The response did not validate. `problems` never contains field values (PII safety)."""

    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


def _strip_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


def parse_extraction(doc_type: str, data: dict[str, Any], page_count: int) -> _Strict:
    """Validate an already-decoded (and already PII-masked) response."""
    try:
        parsed = MODELS[doc_type].model_validate(data)
    except ValidationError as exc:
        raise ExtractionInvalid([
            f"{'.'.join(map(str, e['loc'])) or 'root'}: {e['msg']}"
            for e in exc.errors(include_url=False, include_input=False)]) from exc
    problems = []
    for path, page in _pages(parsed):
        if page is not None and not 1 <= page <= page_count:
            problems.append(f"{path}.page: {page} is outside 1..{page_count}")
    if problems:
        raise ExtractionInvalid(problems)
    return parsed


def decode_json(text: str) -> dict[str, Any]:
    try:
        data = json.loads(_strip_fence(text))
    except json.JSONDecodeError as exc:
        raise ExtractionInvalid([f"response is not valid JSON ({exc.msg})"]) from exc
    if not isinstance(data, dict):
        raise ExtractionInvalid(["response is not a JSON object"])
    return data


def _pages(parsed: BaseModel):
    for name, value in parsed:
        if isinstance(value, _CitedBase):
            yield name, value.page
        elif isinstance(value, list):
            for i, row in enumerate(value):
                yield f"{name}[{i}]", row.page
