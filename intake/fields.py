"""Flatten an extraction into one record per field path.

`total`, `invoice_date`, `line_items[2].amount`, `claims[0].status`, ...

Checks, routing, storage, the eval and the review UI all work on this flat
list, so a "field" means the same thing everywhere. Row fields (line items,
claims) share their row's confidence and citation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

from pydantic import BaseModel

from intake.schemas import ITEM_KEY, CitedDate, CitedInt, CitedMoney, CitedText

_SCALAR_KIND = {CitedText: "text", CitedMoney: "money", CitedDate: "date", CitedInt: "int"}
ROW_KINDS = {
    "line_items": {"description": "text", "quantity": "number", "unit_price": "money",
                   "amount": "money"},
    "claims": {"claim_number": "text", "date_of_loss": "date", "status": "text",
               "paid": "money", "reserved": "money", "incurred": "money"},
}


def jsonable(value: Any) -> Any:
    return value.isoformat() if isinstance(value, date) else value


@dataclass
class FieldView:
    path: str
    kind: str
    value: Any
    confidence: float
    page: int | None
    source_text: str | None
    row: int | None = None
    # filled in by checks / routing
    citation: str = "unchecked"
    flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def flatten(doc_type: str, extraction: BaseModel) -> list[FieldView]:
    out: list[FieldView] = []
    item_key = ITEM_KEY[doc_type]
    for name, value in extraction:
        if name == item_key:
            for i, row in enumerate(value):
                for col, kind in ROW_KINDS[item_key].items():
                    out.append(FieldView(f"{name}[{i}].{col}", kind, jsonable(getattr(row, col)),
                                         row.confidence, row.page, row.source_text, row=i))
        else:
            out.append(FieldView(name, _SCALAR_KIND[type(value)], jsonable(value.value),
                                 value.confidence, value.page, value.source_text))
    return out
