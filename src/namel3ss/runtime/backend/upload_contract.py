from __future__ import annotations

from dataclasses import dataclass, field
import re


DEFAULT_CONTENT_TYPE = "application/octet-stream"

UPLOAD_STATE_ACCEPTED = "accepted"
UPLOAD_STATE_RECEIVING = "receiving"
UPLOAD_STATE_VALIDATED = "validated"
UPLOAD_STATE_REJECTED = "rejected"
UPLOAD_STATE_STORED = "stored"

UPLOAD_STATES = {
    UPLOAD_STATE_ACCEPTED,
    UPLOAD_STATE_RECEIVING,
    UPLOAD_STATE_VALIDATED,
    UPLOAD_STATE_REJECTED,
    UPLOAD_STATE_STORED,
}

UPLOAD_ERROR_BOUNDARY = "upload_boundary_error"
UPLOAD_ERROR_LENGTH = "upload_length_error"
UPLOAD_ERROR_CHUNK = "upload_chunk_error"
UPLOAD_ERROR_FILE = "upload_file_error"
UPLOAD_ERROR_STREAM = "upload_stream_error"
UPLOAD_ERROR_CAPABILITY = "upload_capability_error"

UPLOAD_PROGRESS_STEP_BYTES = 65536

_PDF_PAGE_RE = re.compile(rb"/Type\s*/Page\b")
_PDF_TAIL_SIZE = 64
_TEXT_EXTS = {".txt", ".md", ".csv"}


def clean_upload_filename(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return "upload"
    normalized = raw.replace("\\", "/")
    name = normalized.split("/")[-1].strip()
    return name or "upload"


def build_upload_preview(metadata: dict, counts: dict | None = None) -> dict:
    name = clean_upload_filename(_text_value(metadata.get("name"), "upload"))
    content_type = _text_value(metadata.get("content_type"), DEFAULT_CONTENT_TYPE) or DEFAULT_CONTENT_TYPE
    size = _int_value(metadata.get("bytes") if "bytes" in metadata else metadata.get("size"))
    checksum = _text_value(metadata.get("checksum"), "")
    preview: dict[str, object] = {
        "filename": name,
        "content_type": content_type,
        "size": size,
        "checksum": checksum,
    }
    if counts:
        page_count = counts.get("page_count")
        if isinstance(page_count, int) and page_count >= 0:
            preview["page_count"] = page_count
        item_count = counts.get("item_count")
        if isinstance(item_count, int) and item_count >= 0:
            preview["item_count"] = item_count
    return preview


def build_progress(bytes_received: int, total_bytes: int | None) -> dict:
    return {
        "bytes_received": max(0, int(bytes_received)),
        "total_bytes": _int_or_none(total_bytes),
        "percent_complete": percent_complete(bytes_received, total_bytes),
    }


def percent_complete(bytes_received: int, total_bytes: int | None) -> int | None:
    if total_bytes is None or total_bytes <= 0:
        return None
    received = max(0, int(bytes_received))
    if received <= 0:
        return 0
    if received >= total_bytes:
        return 100
    return int((received * 100) // int(total_bytes))


@dataclass
class UploadProgressTracker:
    total_bytes: int | None
    step_bytes: int = UPLOAD_PROGRESS_STEP_BYTES
    bytes_received: int = 0
    next_boundary: int = field(init=False)
    last_emitted: int | None = None

    def __post_init__(self) -> None:
        self.next_boundary = max(1, int(self.step_bytes))

    def set_total_bytes(self, total_bytes: int | None) -> None:
        self.total_bytes = _int_or_none(total_bytes)

    def snapshot(self) -> dict:
        return build_progress(self.bytes_received, self.total_bytes)

    def advance(self, amount: int) -> list[dict]:
        if amount <= 0:
            return []
        self.bytes_received += int(amount)
        events: list[dict] = []
        while self.step_bytes > 0 and self.bytes_received >= self.next_boundary:
            events.append(build_progress(self.next_boundary, self.total_bytes))
            self.last_emitted = self.next_boundary
            self.next_boundary += self.step_bytes
        return events

    def finalize(self, *, completed: bool) -> list[dict]:
        had_total = self.total_bytes is not None
        if completed and self.total_bytes is None:
            self.total_bytes = max(0, int(self.bytes_received))
        final_bytes = max(0, int(self.bytes_received))
        if self.last_emitted == final_bytes and had_total:
            return []
        self.last_emitted = final_bytes
        return [build_progress(final_bytes, self.total_bytes)]


@dataclass
class UploadPreviewCounter:
    kind: str
    page_count: int = 0
    line_breaks: int = 0
    text_bytes: int = 0
    last_byte: int | None = None
    pdf_tail: bytes = b""

    @classmethod
    def for_upload(cls, *, filename: str, content_type: str | None) -> "UploadPreviewCounter":
        kind = _preview_kind(filename, content_type)
        return cls(kind=kind)

    def consume(self, data: bytes) -> None:
        if not data:
            return
        if self.kind == "text":
            self.text_bytes += len(data)
            self.line_breaks += data.count(b"\n")
            self.last_byte = data[-1]
            return
        if self.kind == "pdf":
            blob = self.pdf_tail + data
            scan_len = max(0, len(blob) - _PDF_TAIL_SIZE)
            if scan_len:
                self.page_count += len(_PDF_PAGE_RE.findall(blob[:scan_len]))
            self.pdf_tail = blob[-_PDF_TAIL_SIZE:]

    def snapshot(self) -> dict:
        if self.kind == "text":
            if self.text_bytes == 0:
                count = 0
            else:
                count = self.line_breaks
                if self.last_byte not in (10,):
                    count += 1
            return {"item_count": count}
        if self.kind == "pdf":
            extra = len(_PDF_PAGE_RE.findall(self.pdf_tail))
            return {"page_count": self.page_count + extra}
        return {}


def _preview_kind(filename: str, content_type: str | None) -> str:
    content = (content_type or "").split(";", 1)[0].strip().lower()
    ext = _extension(filename)
    if content.startswith("text/") or ext in _TEXT_EXTS:
        return "text"
    if content == "application/pdf" or ext == ".pdf":
        return "pdf"
    return "none"


def _extension(name: str) -> str:
    if not name:
        return ""
    dot = name.rfind(".")
    if dot == -1:
        return ""
    return name[dot:].lower()


def _int_value(value: object) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return 0


def _int_or_none(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return None


def _text_value(value: object, default: str) -> str:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned if cleaned else default
    return default


def upload_error_details(code: str, *, category: str = "runtime") -> dict:
    return {"error_id": code, "category": category}


__all__ = [
    "DEFAULT_CONTENT_TYPE",
    "UPLOAD_PROGRESS_STEP_BYTES",
    "UPLOAD_ERROR_BOUNDARY",
    "UPLOAD_ERROR_CAPABILITY",
    "UPLOAD_ERROR_CHUNK",
    "UPLOAD_ERROR_FILE",
    "UPLOAD_ERROR_LENGTH",
    "UPLOAD_ERROR_STREAM",
    "UPLOAD_STATE_ACCEPTED",
    "UPLOAD_STATE_RECEIVING",
    "UPLOAD_STATE_VALIDATED",
    "UPLOAD_STATE_REJECTED",
    "UPLOAD_STATE_STORED",
    "UPLOAD_STATES",
    "UploadPreviewCounter",
    "UploadProgressTracker",
    "build_progress",
    "build_upload_preview",
    "clean_upload_filename",
    "percent_complete",
    "upload_error_details",
]
