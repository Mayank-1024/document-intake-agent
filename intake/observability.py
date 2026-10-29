"""JSON logs with a PII safety net.

Pipeline code logs ids, routes, reason codes, token counts and latency, never
field values. `RedactingFormatter` additionally masks anything shaped like a
full SSN in the final line, in case a value slips into a message.
"""

from __future__ import annotations

import json
import logging

from intake.pii import redact


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {"level": record.levelname, "logger": record.name, "event": record.getMessage()}
        payload.update(getattr(record, "fields", {}))
        return redact(json.dumps(payload, default=str))


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(RedactingFormatter())
    root = logging.getLogger("intake")
    root.handlers[:] = [handler]
    root.setLevel(level)
    root.propagate = False


def log_event(logger: logging.Logger, event: str, **fields) -> None:
    logger.info(event, extra={"fields": fields})
