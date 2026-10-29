"""Runtime configuration, read from environment variables.

A plain frozen dataclass keeps this easy to read; `get_settings()` re-reads
the environment on every call so tests can change variables with monkeypatch.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# USD per million tokens (input, output), Anthropic first-party list prices, checked
# 2026-10-29. Haiku 5.5's price applies to prompts up to 100K tokens; ours are far smaller.
PRICING = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
}


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str | None
    model: str
    effort: str
    max_tokens: int
    timeout_s: float
    sdk_max_retries: int
    confidence_threshold: float
    db_path: Path
    upload_dir: Path
    data_dir: Path


def get_settings() -> Settings:
    return Settings(
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY") or None,
        model=os.environ.get("INTAKE_MODEL", "claude-haiku-5-5"),
        effort=os.environ.get("INTAKE_EFFORT", "medium"),
        max_tokens=int(os.environ.get("INTAKE_MAX_TOKENS", "16000")),
        timeout_s=float(os.environ.get("INTAKE_TIMEOUT_S", "120")),
        sdk_max_retries=int(os.environ.get("INTAKE_SDK_MAX_RETRIES", "3")),
        confidence_threshold=float(os.environ.get("CONFIDENCE_THRESHOLD", "0.90")),
        db_path=Path(os.environ.get("INTAKE_DB", str(ROOT / "intake.db"))),
        upload_dir=Path(os.environ.get("UPLOAD_DIR", str(ROOT / "uploads"))),
        data_dir=Path(os.environ.get("DATA_DIR", str(ROOT / "data"))),
    )


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float | None:
    if model not in PRICING:
        return None
    pin, pout = PRICING[model]
    return (input_tokens * pin + output_tokens * pout) / 1_000_000
