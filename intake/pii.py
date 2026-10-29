"""PII handling. The rule: a full SSN never leaves the request that read it.

- `mask_response` runs on the decoded model response before validation,
  storage, logging or a retry prompt. Any full SSN in any string (value,
  source_text, a line-item description) becomes XXX-XX-1234. The model is told
  to return the masked form; this is the code-side guarantee if it does not.
- `redact` is a last line of defense for log lines and error messages.
- Pydantic error messages are built with include_input=False (intake/schemas.py),
  so a validation error cannot echo a value back into a retry prompt.
"""

from __future__ import annotations

import re
from typing import Any

FULL_SSN = re.compile(r"\b(\d{3})[- ]?(\d{2})[- ]?(\d{4})\b")
MASKED_SSN = re.compile(r"XXX-XX-\d{4}")
# Only treat 9-digit runs as SSNs when they are written with separators, or when the field is
# known to hold an SSN. A bare 9-digit invoice number must not be rewritten.
SEPARATED_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


def mask_ssn(text: str) -> str:
    """Mask a value that is known to be an SSN (any common format)."""
    m = FULL_SSN.search(text)
    return f"XXX-XX-{m.group(3)}" if m else text


def redact(text: str) -> str:
    """Mask every dash-separated SSN in free text."""
    return SEPARATED_SSN.sub(lambda m: "XXX-XX-" + m.group(0)[-4:], text)


def mask_response(data: Any, pii_fields: tuple[str, ...] = ()) -> tuple[Any, int]:
    """Return (masked copy, number of strings changed)."""
    changed = 0

    def walk(node: Any, in_pii: bool) -> Any:
        nonlocal changed
        if isinstance(node, dict):
            return {k: walk(v, in_pii or k in pii_fields) for k, v in node.items()}
        if isinstance(node, list):
            return [walk(v, in_pii) for v in node]
        if isinstance(node, str):
            new = mask_ssn(node) if in_pii else redact(node)
            if new != node:
                changed += 1
            return new
        return node

    return walk(data, False), changed
