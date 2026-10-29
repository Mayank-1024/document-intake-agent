"""Ground-truth loading, in the same flat field-path form the pipeline produces."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from intake.documents import LoadedDocument, load_path
from intake.fields import ROW_KINDS
from intake.schemas import ITEM_KEY, MODELS, CitedDate, CitedInt, CitedMoney, CitedText

DATA = Path(__file__).resolve().parent.parent / "data"
_KIND = {CitedText: "text", CitedMoney: "money", CitedDate: "date", CitedInt: "int"}


@dataclass
class Case:
    truth: dict[str, Any]

    @property
    def doc_id(self) -> str:
        return self.truth["doc_id"]

    @property
    def doc_type(self) -> str:
        return self.truth["doc_type"]

    def load(self, data_dir: Path = DATA) -> LoadedDocument:
        return load_path(data_dir / self.truth["file"])

    def fields(self) -> dict[str, tuple[str, Any]]:
        """path -> (kind, value)"""
        out: dict[str, tuple[str, Any]] = {}
        model = MODELS[self.doc_type]
        for name, f in self.truth["fields"].items():
            out[name] = (_KIND[model.model_fields[name].annotation], f["value"])
        key = ITEM_KEY[self.doc_type]
        if key:
            for i, row in enumerate(self.truth[key]):
                for col, kind in ROW_KINDS[key].items():
                    out[f"{key}[{i}].{col}"] = (kind, row[col])
        return out


def load_cases(data_dir: Path = DATA, ids: list[str] | None = None) -> list[Case]:
    cases = [Case(json.loads(p.read_text())) for p in sorted((data_dir / "truth").glob("*.json"))]
    if ids:
        cases = [c for c in cases if c.doc_id in ids]
    return cases
