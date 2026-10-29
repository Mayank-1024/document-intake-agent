"""Routing: every document ends as `auto_accept` or `needs_review`, with reasons.

A document is auto-accepted only when ALL of these hold:
- the response validated (after at most one retry);
- every required field has a value;
- every field's confidence is at or above the threshold;
- every citation verified against the text layer (so scans never auto-accept);
- every business rule passed (skipped rules do not block).

Each reason names the field or rule behind it, and the implicated fields get
flags. The eval uses those flags to ask a sharper question than "was the
document reviewed": was the specific wrong field pointed out to the reviewer?
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from intake.checks import ABSENT, UNVERIFIABLE, VERIFIED, RuleResult
from intake.fields import FieldView

AUTO_ACCEPT, NEEDS_REVIEW = "auto_accept", "needs_review"


@dataclass
class Reason:
    code: str  # missing_required | low_confidence | citation_failed | no_text_layer |
    #            rule_failed | extraction_invalid | model_error
    detail: str
    field: str | None = None
    rule: str | None = None

    def to_dict(self):
        return asdict(self)


def route(fields: list[FieldView], rules: list[RuleResult], required: tuple[str, ...],
          threshold: float, has_text_layer: bool) -> tuple[str, list[Reason]]:
    reasons: list[Reason] = []
    by_path = {f.path: f for f in fields}

    for name in required:
        f = by_path.get(name)
        if f is None or f.value is None:
            reasons.append(Reason("missing_required", f"required field {name} is empty", name))
            if f is not None:
                f.flags.append("missing_required")

    for f in fields:
        if f.confidence < threshold:
            reasons.append(Reason("low_confidence",
                                  f"{f.path} confidence {f.confidence:.2f} < {threshold:.2f}",
                                  f.path))
            f.flags.append("low_confidence")
        if f.citation not in (VERIFIED, UNVERIFIABLE, ABSENT):
            reasons.append(Reason("citation_failed", f"{f.path} citation {f.citation}", f.path))
            f.flags.append(f"citation:{f.citation}")

    if not has_text_layer:
        reasons.append(Reason("no_text_layer",
                              "scanned document: citations cannot be checked against text"))

    for r in rules:
        if r.status == "fail":
            reasons.append(Reason("rule_failed", r.detail, rule=r.rule))
            for path in r.fields:
                if path in by_path:
                    by_path[path].flags.append(f"rule:{r.rule}")

    return (NEEDS_REVIEW if reasons else AUTO_ACCEPT), reasons


def failed_route(code: str, detail: str) -> tuple[str, list[Reason]]:
    return NEEDS_REVIEW, [Reason(code, detail)]
