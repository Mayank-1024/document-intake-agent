"""Offline ExtractionModel: replays prepared JSON answers. No network, no key.

Answers are keyed by the SHA-256 of the document bytes, read back out of the
base64 content block, so the fake sees exactly what Claude would. Each
document can have a list of answers (attempt 1, attempt 2) to exercise the
retry path. `answer_from_truth` builds a perfect answer from a ground-truth
file, using the printed text recorded by the generator as the citation.
"""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from intake.model_client import ModelError, ModelResponse
from intake.schemas import ITEM_KEY

ROW_COLUMNS = {
    "line_items": ("description", "quantity", "unit_price", "amount"),
    "claims": ("claim_number", "date_of_loss", "status", "paid", "reserved", "incurred"),
}


def answer_from_truth(truth: dict[str, Any], confidence: float = 0.97) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, f in truth["fields"].items():
        absent = f["value"] is None
        out[name] = {"value": f["value"], "confidence": confidence,
                     "page": None if absent else f["page"],
                     "source_text": None if absent else f["text"]}
    key = ITEM_KEY[truth["doc_type"]]
    if key:
        out[key] = [{**{c: row[c] for c in ROW_COLUMNS[key]}, "confidence": confidence,
                     "page": row["page"], "source_text": row["text"]} for row in truth[key]]
    return out


class ScriptedModel:
    name = "scripted"

    def __init__(self, answers: dict[str, list[str | dict]]):
        self._answers = answers  # sha256 -> answers in attempt order
        self._calls: dict[str, int] = {}
        self.requests: list[dict[str, Any]] = []

    def complete(self, *, system: str, content: list[dict[str, Any]],
                 schema: dict[str, Any]) -> ModelResponse:
        self.requests.append({"system": system, "content": content, "schema": schema})
        sha = hashlib.sha256(base64.standard_b64decode(content[0]["source"]["data"])).hexdigest()
        script = self._answers.get(sha)
        if not script:
            raise ModelError("offline model has no answer for this document "
                             "(set ANTHROPIC_API_KEY to use Claude)")
        n = self._calls.get(sha, 0)
        self._calls[sha] = n + 1
        answer = script[min(n, len(script) - 1)]
        return ModelResponse(text=answer if isinstance(answer, str) else json.dumps(answer),
                             stop_reason="end_turn")
