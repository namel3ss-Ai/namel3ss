from __future__ import annotations

import re


_PDF_PAGE_RE = re.compile(rb"/Type\s*/Page\b")
_PDF_IMAGE_RE = re.compile(rb"/Subtype\s*/Image\b")


def detect_upload(metadata: dict, *, content: bytes | None = None) -> dict:
    content_type = str(metadata.get("content_type") or "").lower()
    name = str(metadata.get("name") or "")
    ext = _extension(name)
    kind = _detect_type(content_type, ext)
    page_count = None
    has_images = None
    if kind == "pdf" and content is not None:
        page_count = _pdf_page_count(content)
        has_images = _pdf_has_images(content)
    return {
        "type": kind,
        "page_count": page_count,
        "has_images": has_images,
    }


def _detect_type(content_type: str, ext: str) -> str:
    if content_type.startswith("text/") or ext in {".txt", ".md", ".csv"}:
        return "text"
    if content_type == "application/pdf" or ext == ".pdf":
        return "pdf"
    if content_type in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    } or ext == ".docx":
        return "docx"
    if content_type.startswith("image/") or ext in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff"}:
        return "image"
    return "text"


def _extension(name: str) -> str:
    if not name:
        return ""
    dot = name.rfind(".")
    if dot == -1:
        return ""
    return name[dot:].lower()


def _pdf_page_count(content: bytes) -> int:
    matches = list(_PDF_PAGE_RE.finditer(content))
    return len(matches)


def _pdf_has_images(content: bytes) -> bool:
    return _PDF_IMAGE_RE.search(content) is not None


__all__ = ["detect_upload"]
