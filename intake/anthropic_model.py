"""ExtractionModel backed by the Claude Messages API (anthropic SDK 2.x).

- The document goes in as a native content block: `document` (base64 PDF) or
  `image` (base64 PNG/JPEG). Claude reads the rendered pages; nothing is
  OCR'd locally.
- The answer is constrained with structured outputs (`output_config.format`,
  a JSON Schema built from the pydantic models). The API's native citations
  feature cannot be combined with structured outputs, so the model writes its
  own `source_text` citations and intake/checks.py verifies them.
- Transient errors (429, 5xx, timeouts) are retried by the SDK
  (`max_retries`); anything that still fails becomes ModelError.
"""

from __future__ import annotations

from typing import Any

import anthropic

from intake.model_client import ModelError, ModelResponse


class AnthropicModel:
    def __init__(self, model: str, *, effort: str = "medium", max_tokens: int = 16000,
                 timeout_s: float = 120.0, max_retries: int = 3, client: Any | None = None):
        self.name = model
        self.effort = effort
        self.max_tokens = max_tokens
        self._client = client or anthropic.Anthropic(max_retries=max_retries, timeout=timeout_s)

    def complete(self, *, system: str, content: list[dict[str, Any]],
                 schema: dict[str, Any]) -> ModelResponse:
        try:
            response = self._client.messages.create(
                model=self.name,
                max_tokens=self.max_tokens,
                system=system,
                messages=[{"role": "user", "content": content}],
                output_config={"effort": self.effort,
                               "format": {"type": "json_schema", "schema": schema}},
            )
        except anthropic.APIConnectionError as exc:  # includes APITimeoutError
            raise ModelError(f"connection/timeout after retries: {type(exc).__name__}") from exc
        except anthropic.RateLimitError as exc:
            raise ModelError("rate limited after retries") from exc
        except anthropic.APIStatusError as exc:
            raise ModelError(f"API error {exc.status_code}") from exc

        if response.stop_reason == "refusal":
            raise ModelError("model refused the request")
        text = "".join(b.text for b in response.content if b.type == "text")
        usage = response.usage
        return ModelResponse(text=text, stop_reason=response.stop_reason or "",
                             input_tokens=getattr(usage, "input_tokens", 0) or 0,
                             output_tokens=getattr(usage, "output_tokens", 0) or 0)
