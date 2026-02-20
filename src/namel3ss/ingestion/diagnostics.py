from __future__ import annotations

from typing import Iterable

from namel3ss.config.model import AppConfig
from namel3ss.ingestion.gate_contract import PROBE_REASON_ORDER, QUALITY_REASON_ORDER

_UNKNOWN_REASON_MESSAGE = "Ingestion reported an unknown reason code."
_UNKNOWN_REASON_REMEDIATION = "Review the upload, then re-run ingestion or replace the file."

_REASON_MESSAGES: dict[str, tuple[str, str]] = {
    "empty_content": (
        "The upload is empty.",
        "Upload a file that contains content.",
    ),
    "null_bytes": (
        "Null bytes were detected in the upload.",
        "Upload a text-based file or convert the document to UTF-8 text.",
    ),
    "size_limit": (
        "The upload is too large for ingestion limits.",
        "Split the document into smaller files and upload again.",
    ),
    "utf8_invalid": (
        "The upload has invalid UTF-8 byte sequences.",
        "Convert the file to valid UTF-8 text before uploading.",
    ),
    "binary_markers": (
        "Binary markers were detected in text content.",
        "Upload plain text or use a supported document format.",
    ),
    "pdf_missing_eof": (
        "The PDF appears truncated or missing EOF markers.",
        "Regenerate the PDF and upload a complete file.",
    ),
    "text_too_short": (
        "Extracted text is too short for reliable indexing.",
        "Upload a fuller text document or run OCR for scanned PDFs.",
    ),
    "low_unique_tokens": (
        "Low number of unique tokens; content may be repetitive.",
        "Upload a clearer source file with richer text content.",
    ),
    "high_non_ascii": (
        "A high share of non-ASCII characters was detected.",
        "Check text encoding and upload a normalized UTF-8 document.",
    ),
    "repeated_lines": (
        "Many lines are repeated.",
        "Remove duplicated sections and upload a cleaner document.",
    ),
    "table_heavy": (
        "Content is heavily table-like and may chunk poorly.",
        "Convert critical tables to readable prose or CSV with context.",
    ),
    "many_empty_pages": (
        "Many pages are empty after extraction.",
        "Remove blank pages or upload a text-based source file.",
    ),
    "unreadable_text_pattern": (
        "Extracted text appears unreadable (cipher-like uppercase pattern).",
        "Upload a text-searchable PDF or OCR output, then re-run ingestion.",
    ),
    "empty_text": (
        "No extractable text was found.",
        "Run OCR or upload a PDF with embedded text.",
    ),
    "ocr_failed": (
        "OCR fallback failed; provide a text-based PDF.",
        "Upload a PDF with embedded text or fix local OCR dependencies.",
    ),
    "skipped": (
        "Ingestion was skipped for this upload.",
        "Run ingestion again or replace the upload with a better source file.",
    ),
}

_REASON_ORDER: tuple[str, ...] = tuple(PROBE_REASON_ORDER) + tuple(QUALITY_REASON_ORDER) + ("ocr_failed", "skipped")


def diagnostics_enabled(config: AppConfig | None) -> bool:
    if config is None:
        return True
    ingestion_cfg = getattr(config, "ingestion", None)
    value = getattr(ingestion_cfg, "enable_diagnostics", True)
    return bool(value)


def canonical_reason_codes(reasons: Iterable[str]) -> list[str]:
    raw = [value for value in reasons if isinstance(value, str) and value]
    if not raw:
        return []
    seen: set[str] = set()
    ordered: list[str] = []
    for reason in _REASON_ORDER:
        if reason in raw and reason not in seen:
            ordered.append(reason)
            seen.add(reason)
    for reason in raw:
        if reason not in seen:
            ordered.append(reason)
            seen.add(reason)
    return ordered


def get_reason_details(reasons: Iterable[str]) -> list[dict[str, str]]:
    details: list[dict[str, str]] = []
    for code in canonical_reason_codes(reasons):
        message, remediation = _REASON_MESSAGES.get(code, (_UNKNOWN_REASON_MESSAGE, _UNKNOWN_REASON_REMEDIATION))
        details.append(
            {
                "code": code,
                "message": message,
                "remediation": remediation,
            }
        )
    return details


__all__ = [
    "canonical_reason_codes",
    "diagnostics_enabled",
    "get_reason_details",
]
