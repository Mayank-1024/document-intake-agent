"""process(): document in, routed result out.

    load -> extract (Claude, 1 retry) -> flatten -> verify citations
         -> business rules -> route -> IntakeResult

Everything after `extract` is deterministic code.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from intake.checks import RuleResult, run_rules, verify_citations
from intake.documents import LoadedDocument
from intake.extract import extract
from intake.fields import FieldView, flatten
from intake.model_client import ExtractionModel, ModelError
from intake.observability import log_event
from intake.routing import Reason, failed_route, route
from intake.schemas import DOC_TYPES, REQUIRED
from settings import cost_usd

log = logging.getLogger("intake.pipeline")


@dataclass
class IntakeResult:
    document_id: str
    filename: str
    doc_type: str
    sha256: str
    model: str
    route: str
    reasons: list[Reason]
    fields: list[FieldView]
    rules: list[RuleResult]
    page_count: int
    has_text_layer: bool
    attempts: int
    input_tokens: int
    output_tokens: int
    cost_usd: float | None
    latency_ms: float
    pii_masked: int
    extraction: dict[str, Any] | None = None  # masked, JSON-ready
    validation_problems: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def process(doc: LoadedDocument, doc_type: str, model: ExtractionModel, *,
            threshold: float, document_id: str | None = None) -> IntakeResult:
    if doc_type not in DOC_TYPES:
        raise ValueError(f"doc_type must be one of {DOC_TYPES}")
    t0 = time.perf_counter()
    document_id = document_id or uuid.uuid4().hex[:12]
    fields: list[FieldView] = []
    rules: list[RuleResult] = []
    extraction_json = None
    attempts = in_tok = out_tok = pii_masked = 0
    problems: list[str] = []
    try:
        outcome = extract(doc, doc_type, model)
        attempts, in_tok, out_tok = outcome.attempts, outcome.input_tokens, outcome.output_tokens
        pii_masked, problems = outcome.pii_masked, outcome.problems
        if outcome.extraction is None:
            decision, reasons = failed_route(
                "extraction_invalid", f"response invalid after {attempts} attempts")
        else:
            fields = flatten(doc_type, outcome.extraction)
            verify_citations(doc_type, fields, doc)
            rules = run_rules(doc_type, outcome.extraction)
            decision, reasons = route(fields, rules, REQUIRED[doc_type], threshold,
                                      doc.has_text_layer)
            extraction_json = outcome.extraction.model_dump(mode="json")
    except ModelError as exc:
        decision, reasons = failed_route("model_error", str(exc))

    result = IntakeResult(
        document_id=document_id, filename=doc.name, doc_type=doc_type, sha256=doc.sha256,
        model=model.name, route=decision, reasons=reasons, fields=fields, rules=rules,
        page_count=doc.page_count, has_text_layer=doc.has_text_layer, attempts=attempts,
        input_tokens=in_tok, output_tokens=out_tok, cost_usd=cost_usd(model.name, in_tok, out_tok),
        latency_ms=round((time.perf_counter() - t0) * 1000, 1), pii_masked=pii_masked,
        extraction=extraction_json, validation_problems=problems)
    log_event(log, "document_processed", document_id=document_id, doc_type=doc_type,
              route=decision, reasons=sorted({r.code for r in reasons}), attempts=attempts,
              input_tokens=in_tok, output_tokens=out_tok, latency_ms=result.latency_ms)
    return result
