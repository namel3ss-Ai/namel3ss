from __future__ import annotations

from namel3ss.ingestion.detect import detect_upload
from namel3ss.ingestion.extract import extract_pages, extract_pages_fallback
from namel3ss.ingestion.normalize import normalize_text
from namel3ss.rag.determinism.text_normalizer import canonical_text


PARSER_VERSION = "rag.parser@1"
_ALLOWED_MODES = {"primary", "layout", "ocr"}


def parse_document_bytes(
    *,
    content: bytes,
    metadata: dict[str, object] | None = None,
    mode: str | None = None,
    parser_version: str = PARSER_VERSION,
) -> dict[str, object]:
    metadata_map = _metadata(metadata)
    parse_mode = _mode_value(mode)
    detected = detect_upload(metadata_map, content=content)
    pages, method_used = extract_pages(content, detected=detected, mode=parse_mode)
    normalized_pages = _normalize_pages(pages, expected_pages=_expected_page_count(detected))
    fallback_used = False
    if _needs_fallback(normalized_pages):
        fallback_pages, fallback_method = extract_pages_fallback(content, detected=detected)
        normalized_fallback = _normalize_pages(fallback_pages, expected_pages=_expected_page_count(detected))
        if normalized_fallback:
            normalized_pages = normalized_fallback
            method_used = fallback_method
            fallback_used = True
    if not normalized_pages:
        normalized_pages = [""]
    return {
        "schema_version": parser_version.strip() or PARSER_VERSION,
        "detected": detected,
        "method_used": str(method_used or "").strip() or "primary",
        "fallback_used": fallback_used,
        "pages": normalized_pages,
    }


def _metadata(value: dict[str, object] | None) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    return {str(key): value[key] for key in sorted(value.keys(), key=str)}


def _mode_value(value: str | None) -> str:
    if not isinstance(value, str):
        return "primary"
    text = value.strip().lower()
    if text in _ALLOWED_MODES:
        return text
    return "primary"


def _expected_page_count(detected: dict[str, object]) -> int | None:
    page_count = detected.get("page_count")
    if isinstance(page_count, int) and page_count > 0:
        return page_count
    return None


def _normalize_pages(pages: list[str], *, expected_pages: int | None) -> list[str]:
    rows: list[str] = []
    for page in pages:
        text = _normalize_page(page)
        rows.append(text)
    rows = _align_page_count(rows, expected_pages=expected_pages)
    return rows


def _normalize_page(value: object) -> str:
    raw = value if isinstance(value, str) else ""
    normalized = normalize_text(raw)
    return canonical_text(normalized)


def _align_page_count(pages: list[str], *, expected_pages: int | None) -> list[str]:
    if expected_pages is None:
        return pages
    if len(pages) >= expected_pages:
        return pages[:expected_pages]
    extended = list(pages)
    while len(extended) < expected_pages:
        extended.append("")
    return extended


def _needs_fallback(pages: list[str]) -> bool:
    if not pages:
        return True
    return all(not page for page in pages)


__all__ = [
    "PARSER_VERSION",
    "parse_document_bytes",
]
