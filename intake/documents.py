"""Loading a document: bytes for the API, plus the text layer for citation checks.

PDFs go to the API as native `document` blocks; PNG/JPEG go as `image` blocks.
No OCR runs locally. The text layer (from pypdf) is used only to verify
citations; it is never sent to the model, so the model cannot copy from it.
A PDF made of page images (a scan) has no text layer, and its citations are
marked unverifiable.
"""

from __future__ import annotations

import base64
import hashlib
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

MEDIA_TYPES = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg",
               ".jpeg": "image/jpeg"}
MIN_TEXT_CHARS = 20  # fewer extractable characters than this on every page means "scan"


@dataclass(frozen=True)
class LoadedDocument:
    name: str
    media_type: str
    data: bytes
    page_count: int
    page_texts: list[str] | None  # None when there is no usable text layer
    sha256: str

    @property
    def has_text_layer(self) -> bool:
        return self.page_texts is not None

    def content_block(self) -> dict:
        b64 = base64.standard_b64encode(self.data).decode("ascii")
        block_type = "document" if self.media_type == "application/pdf" else "image"
        return {"type": block_type,
                "source": {"type": "base64", "media_type": self.media_type, "data": b64}}


def load_bytes(name: str, data: bytes, media_type: str | None = None) -> LoadedDocument:
    media_type = media_type or MEDIA_TYPES.get(Path(name).suffix.lower())
    if media_type not in MEDIA_TYPES.values():
        raise ValueError(f"unsupported document type for {name!r}; use PDF, PNG or JPEG")
    sha = hashlib.sha256(data).hexdigest()
    if media_type != "application/pdf":
        return LoadedDocument(name, media_type, data, 1, None, sha)
    reader = PdfReader(BytesIO(data))
    texts = [page.extract_text() or "" for page in reader.pages]
    has_text = any(len(t.strip()) >= MIN_TEXT_CHARS for t in texts)
    return LoadedDocument(name, media_type, data, len(reader.pages), texts if has_text else None,
                          sha)


def load_path(path: Path) -> LoadedDocument:
    return load_bytes(path.name, path.read_bytes())


_NON_TEXT = re.compile(r"\s+")


def squash(text: str) -> str:
    """Normalization for citation matching: case-insensitive and whitespace-free.

    Removing whitespace entirely (rather than collapsing it) makes matching robust to
    how a PDF splits a table row into separate text runs or lines.
    """
    return _NON_TEXT.sub("", text).casefold()
