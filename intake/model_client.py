"""The seam between the pipeline and any language model.

The pipeline depends only on this protocol, so the same code runs against
Claude for real and against a scripted fake in tests and offline evals.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class ModelResponse:
    text: str  # concatenated text blocks: the JSON answer
    stop_reason: str
    input_tokens: int = 0
    output_tokens: int = 0


class ModelError(Exception):
    """The call failed for good (after the SDK's own retries), or the model refused."""


class ExtractionModel(Protocol):
    name: str

    def complete(self, *, system: str, content: list[dict[str, Any]],
                 schema: dict[str, Any]) -> ModelResponse: ...
