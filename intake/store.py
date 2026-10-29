"""SQLite persistence: processed documents, the review queue, reviewer actions.

Stdlib sqlite3, one connection per call, so the API can share a Store across
threads. Every stored value has already been PII-masked by the pipeline;
corrections to a PII field are masked again here before they are written.

Tables
  documents       one row per processed document; the full IntakeResult as JSON
  review_actions  approve / correct events, in order. Corrections keep the old
                  and new value and the document's sha256, so they can be
                  exported as ground truth for future evals.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from intake.pii import mask_ssn
from intake.pipeline import IntakeResult
from intake.routing import NEEDS_REVIEW
from intake.schemas import PII_FIELDS

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id          TEXT PRIMARY KEY,
    filename    TEXT NOT NULL,
    doc_type    TEXT NOT NULL,
    sha256      TEXT NOT NULL,
    route       TEXT NOT NULL,           -- auto_accept | needs_review (as decided by the pipeline)
    status      TEXT NOT NULL,           -- auto_accepted | in_review | approved | corrected
    model       TEXT NOT NULL,
    file_path   TEXT,
    result_json TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS documents_status ON documents(status);
CREATE TABLE IF NOT EXISTS review_actions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id    TEXT NOT NULL REFERENCES documents(id),
    action         TEXT NOT NULL,        -- approve | correct
    field          TEXT,
    previous_value TEXT,                 -- JSON
    new_value      TEXT,                 -- JSON
    reviewer       TEXT NOT NULL,
    note           TEXT,
    created_at     TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class NotFound(KeyError):
    pass


class InvalidAction(ValueError):
    pass


class Store:
    def __init__(self, path: Path | str):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------ documents

    def save_result(self, result: IntakeResult, file_path: str | None = None) -> None:
        status = "in_review" if result.route == NEEDS_REVIEW else "auto_accepted"
        now = _now()
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (result.document_id, result.filename, result.doc_type, result.sha256,
                 result.route, status, result.model, file_path,
                 json.dumps(result.to_dict(), default=str), now, now))

    def get(self, document_id: str) -> dict[str, Any]:
        with self._conn() as c:
            row = c.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
            if row is None:
                raise NotFound(document_id)
            actions = c.execute("SELECT * FROM review_actions WHERE document_id = ? ORDER BY id",
                                (document_id,)).fetchall()
        return self._doc(row, actions)

    def file_path(self, document_id: str) -> str | None:
        with self._conn() as c:
            row = c.execute("SELECT file_path FROM documents WHERE id = ?",
                            (document_id,)).fetchone()
        if row is None:
            raise NotFound(document_id)
        return row["file_path"]

    def review_queue(self) -> list[dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM documents WHERE status = 'in_review' "
                             "ORDER BY created_at, id").fetchall()
        return [self._summary(r) for r in rows]

    def list_documents(self) -> list[dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM documents ORDER BY created_at, id").fetchall()
        return [self._summary(r) for r in rows]

    # ------------------------------------------------------------ reviewer actions

    def approve(self, document_id: str, reviewer: str, note: str | None = None) -> dict:
        doc = self.get(document_id)
        if doc["status"] != "in_review":
            raise InvalidAction(f"document is {doc['status']}, not in_review")
        with self._conn() as c:
            c.execute("INSERT INTO review_actions (document_id, action, reviewer, note, created_at)"
                      " VALUES (?, 'approve', ?, ?, ?)", (document_id, reviewer, note, _now()))
            final = "corrected" if any(a["action"] == "correct" for a in doc["actions"]) \
                else "approved"
            c.execute("UPDATE documents SET status = ?, updated_at = ? WHERE id = ?",
                      (final, _now(), document_id))
        return self.get(document_id)

    def correct(self, document_id: str, field: str, value: Any, reviewer: str,
                note: str | None = None) -> dict:
        """Record a corrected value. The document stays in review until approved."""
        doc = self.get(document_id)
        if doc["status"] != "in_review":
            raise InvalidAction(f"document is {doc['status']}, not in_review")
        fields = {f["path"]: f for f in doc["result"]["fields"]}
        if field not in fields:
            raise InvalidAction(f"unknown field {field!r}")
        if field in PII_FIELDS.get(doc["doc_type"], ()) and isinstance(value, str):
            value = mask_ssn(value)
        with self._conn() as c:
            c.execute("INSERT INTO review_actions (document_id, action, field, previous_value, "
                      "new_value, reviewer, note, created_at) VALUES (?, 'correct', ?, ?, ?, ?, "
                      "?, ?)", (document_id, field, json.dumps(fields[field]["value"]),
                                json.dumps(value), reviewer, note, _now()))
        return self.get(document_id)

    def corrections(self) -> list[dict[str, Any]]:
        """Every correction, in the field-path format the eval's ground truth uses."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT a.*, d.sha256, d.doc_type, d.filename FROM review_actions a "
                "JOIN documents d ON d.id = a.document_id WHERE a.action = 'correct' "
                "ORDER BY a.id").fetchall()
        return [{"document_id": r["document_id"], "sha256": r["sha256"],
                 "doc_type": r["doc_type"], "filename": r["filename"], "field": r["field"],
                 "previous_value": json.loads(r["previous_value"]),
                 "corrected_value": json.loads(r["new_value"]), "reviewer": r["reviewer"],
                 "created_at": r["created_at"]} for r in rows]

    # ------------------------------------------------------------ helpers

    @staticmethod
    def _summary(row: sqlite3.Row) -> dict[str, Any]:
        result = json.loads(row["result_json"])
        return {"id": row["id"], "filename": row["filename"], "doc_type": row["doc_type"],
                "route": row["route"], "status": row["status"], "model": row["model"],
                "created_at": row["created_at"],
                "reason_codes": sorted({r["code"] for r in result["reasons"]}),
                "flagged_fields": sum(bool(f["flags"]) for f in result["fields"])}

    def _doc(self, row: sqlite3.Row, actions: list[sqlite3.Row]) -> dict[str, Any]:
        out = self._summary(row)
        out["result"] = json.loads(row["result_json"])
        out["actions"] = [{"action": a["action"], "field": a["field"],
                           "previous_value": json.loads(a["previous_value"])
                           if a["previous_value"] else None,
                           "new_value": json.loads(a["new_value"]) if a["new_value"] else None,
                           "reviewer": a["reviewer"], "note": a["note"],
                           "created_at": a["created_at"]} for a in actions]
        # current values = extracted values with corrections applied, latest wins
        current = {f["path"]: f["value"] for f in out["result"]["fields"]}
        for a in out["actions"]:
            if a["action"] == "correct":
                current[a["field"]] = a["new_value"]
        out["current_values"] = current
        return out
