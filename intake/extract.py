"""One extraction call, validated, with exactly one retry.

attempt 1 -> decode JSON -> mask PII -> pydantic + page-range validation
  valid   -> done
  invalid -> attempt 2 with the validation problems (never the values) appended
  invalid -> give up: the pipeline routes the document to review

The retry is a fresh request rather than a continuation of the conversation,
so no thinking blocks or partial answers have to be replayed.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from pydantic import BaseModel

from intake.documents import LoadedDocument
from intake.model_client import ExtractionModel
from intake.pii import mask_response
from intake.prompts import SYSTEM, user_prompt
from intake.schemas import (
    PII_FIELDS,
    ExtractionInvalid,
    decode_json,
    output_json_schema,
    parse_extraction,
)

MAX_ATTEMPTS = 2


@dataclass
class ExtractionOutcome:
    extraction: BaseModel | None
    attempts: int = 0
    problems: list[str] = field(default_factory=list)  # from the last failed attempt
    input_tokens: int = 0
    output_tokens: int = 0
    model_latency_ms: float = 0.0
    pii_masked: int = 0  # strings the code had to mask because the model did not


def extract(doc: LoadedDocument, doc_type: str, model: ExtractionModel) -> ExtractionOutcome:
    """Raises ModelError if the API call itself fails."""
    schema = output_json_schema(doc_type)
    out = ExtractionOutcome(extraction=None)
    problems: list[str] | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        content = [doc.content_block(),
                   {"type": "text", "text": user_prompt(doc_type, doc.page_count, problems)}]
        t0 = time.perf_counter()
        resp = model.complete(system=SYSTEM, content=content, schema=schema)
        out.model_latency_ms += (time.perf_counter() - t0) * 1000
        out.attempts = attempt
        out.input_tokens += resp.input_tokens
        out.output_tokens += resp.output_tokens
        try:
            if resp.stop_reason == "max_tokens":
                raise ExtractionInvalid(["response was cut off at max_tokens"])
            data, masked = mask_response(decode_json(resp.text), PII_FIELDS.get(doc_type, ()))
            out.pii_masked += masked
            out.extraction = parse_extraction(doc_type, data, doc.page_count)
            out.problems = []
            return out
        except ExtractionInvalid as exc:
            problems = exc.problems[:20]
            out.problems = problems
    return out
