"""HTTP API for the intake pipeline and the review queue.

    uv run uvicorn api.main:create_app --factory --port 8000

POST /documents                    multipart: file (PDF/PNG/JPEG) + doc_type
GET  /documents                    all processed documents (summaries)
GET  /documents/{id}               full result: fields, citations, checks, reasons, actions
GET  /documents/{id}/file          the original upload (for the review UI)
GET  /review-queue                 documents waiting for a reviewer
POST /documents/{id}/corrections   {field, value, reviewer, note?}
POST /documents/{id}/approve       {reviewer, note?}  closes the review
GET  /corrections                  every correction, for building new ground truth
GET  /healthz

Processing runs inside the request (a document takes seconds with the real
model). Without ANTHROPIC_API_KEY the service uses an offline model that only
knows the 30 dataset documents, so the demo works with no key.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from intake.anthropic_model import AnthropicModel
from intake.documents import MEDIA_TYPES, load_bytes
from intake.model_client import ExtractionModel
from intake.observability import configure_logging
from intake.pipeline import process
from intake.schemas import DOC_TYPES
from intake.scripted_model import ScriptedModel, answer_from_truth
from intake.store import InvalidAction, NotFound, Store
from settings import get_settings

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


class CorrectionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str = Field(min_length=1)
    value: Any
    reviewer: str = Field(min_length=1, max_length=100)
    note: str | None = Field(default=None, max_length=1000)


class ApproveIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reviewer: str = Field(min_length=1, max_length=100)
    note: str | None = Field(default=None, max_length=1000)


def offline_dataset_model(data_dir: Path) -> ScriptedModel:
    answers = {}
    for p in sorted((data_dir / "truth").glob("*.json")):
        truth = json.loads(p.read_text())
        doc = load_bytes(truth["file"], (data_dir / truth["file"]).read_bytes())
        answers[doc.sha256] = [answer_from_truth(truth)]
    return ScriptedModel(answers)


def default_model() -> ExtractionModel:
    s = get_settings()
    if s.anthropic_api_key:
        return AnthropicModel(s.model, effort=s.effort, max_tokens=s.max_tokens,
                              timeout_s=s.timeout_s, max_retries=s.sdk_max_retries)
    return offline_dataset_model(s.data_dir)


def create_app(store: Store | None = None, model: ExtractionModel | None = None,
               upload_dir: Path | None = None, threshold: float | None = None) -> FastAPI:
    s = get_settings()
    store = store or Store(s.db_path)
    model = model or default_model()
    upload_dir = upload_dir or s.upload_dir
    threshold = s.confidence_threshold if threshold is None else threshold
    configure_logging()
    app = FastAPI(title="Document Intake Agent", version="0.1.0")

    def _get(document_id: str) -> dict:
        try:
            return store.get(document_id)
        except NotFound:
            raise HTTPException(404, "document not found") from None

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "model": model.name, "threshold": threshold}

    @app.post("/documents", status_code=201)
    def upload(file: Annotated[UploadFile, File()], doc_type: Annotated[str, Form()]):
        if doc_type not in DOC_TYPES:
            raise HTTPException(422, f"doc_type must be one of {list(DOC_TYPES)}")
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in MEDIA_TYPES:
            raise HTTPException(415, "upload a PDF, PNG or JPEG")
        data = file.file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "file is larger than 10 MB")
        try:
            doc = load_bytes(file.filename or f"upload{suffix}", data)
        except Exception:
            raise HTTPException(422, "could not read the document") from None
        result = process(doc, doc_type, model, threshold=threshold)
        upload_dir.mkdir(parents=True, exist_ok=True)
        path = upload_dir / f"{result.document_id}{suffix}"
        path.write_bytes(data)
        store.save_result(result, file_path=str(path))
        return _get(result.document_id)

    @app.get("/documents")
    def list_documents():
        return store.list_documents()

    @app.get("/documents/{document_id}")
    def get_document(document_id: str):
        return _get(document_id)

    @app.get("/documents/{document_id}/file")
    def get_file(document_id: str):
        try:
            path = store.file_path(document_id)
        except NotFound:
            raise HTTPException(404, "document not found") from None
        if not path or not Path(path).exists():
            raise HTTPException(404, "file not stored")
        return FileResponse(path, media_type=MEDIA_TYPES[Path(path).suffix.lower()])

    @app.get("/review-queue")
    def review_queue():
        return store.review_queue()

    @app.post("/documents/{document_id}/corrections")
    def correct(document_id: str, body: CorrectionIn):
        _get(document_id)
        try:
            return store.correct(document_id, body.field, body.value, body.reviewer, body.note)
        except InvalidAction as exc:
            raise HTTPException(409, str(exc)) from None

    @app.post("/documents/{document_id}/approve")
    def approve(document_id: str, body: ApproveIn):
        _get(document_id)
        try:
            return store.approve(document_id, body.reviewer, body.note)
        except InvalidAction as exc:
            raise HTTPException(409, str(exc)) from None

    @app.get("/corrections")
    def corrections():
        return store.corrections()

    return app

