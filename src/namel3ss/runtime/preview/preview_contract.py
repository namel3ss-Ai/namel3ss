from __future__ import annotations

from typing import Mapping


PREVIEW_UNION_CONTRACT_ERROR_CODE = "N3E_PREVIEW_UNION_CONTRACT_VIOLATION"
PREVIEW_STATUS_OK = "ok"
PREVIEW_STATUS_UNAVAILABLE = "unavailable"
PREVIEW_UNAVAILABLE_REASON_NON_PDF = "preview_non_pdf"
PREVIEW_UNAVAILABLE_REASON_PAGE_TEXT = "preview_page_text_unavailable"
PREVIEW_UNAVAILABLE_REASON_UNKNOWN = "preview_unavailable"


def build_preview_ok_payload(page_payload: Mapping[str, object]) -> dict[str, object]:
    document = _mapping(page_payload.get("document"))
    page = _mapping(page_payload.get("page"))
    return {
        "doc_meta": {
            "checksum": _text(document.get("checksum")),
            "document_id": _text(document.get("document_id")),
            "page_count": _int_value(document.get("page_count")),
            "requested_page": _int_value(page.get("number")),
            "source_name": _text(document.get("source_name")),
        },
        "fallback_snippet": "",
        "highlights": _list_of_maps(page_payload.get("highlights")),
        "page": {
            "number": _int_value(page.get("number")),
            "text": _text(page.get("text")),
        },
        "pdf_url": _text(page_payload.get("pdf_url")),
        "reason": "",
        "reason_code": "",
        "status": PREVIEW_STATUS_OK,
    }


def build_preview_unavailable_payload(
    *,
    document_id: str,
    page_number: object,
    reason_code: str,
    reason: str,
    fallback_snippet: str = "",
    source_name: str = "",
    page_count: int = 0,
    checksum: str = "",
) -> dict[str, object]:
    return {
        "doc_meta": {
            "checksum": checksum.strip(),
            "document_id": document_id.strip(),
            "page_count": page_count if page_count > 0 else 0,
            "requested_page": _int_value(page_number),
            "source_name": source_name.strip(),
        },
        "fallback_snippet": fallback_snippet.strip(),
        "highlights": [],
        "page": {"number": _int_value(page_number), "text": ""},
        "pdf_url": "",
        "reason": reason.strip(),
        "reason_code": reason_code.strip() or PREVIEW_UNAVAILABLE_REASON_UNKNOWN,
        "status": PREVIEW_STATUS_UNAVAILABLE,
    }


def validate_preview_union_payload(payload: Mapping[str, object]) -> dict[str, object]:
    status = _text(payload.get("status"))
    if status not in {PREVIEW_STATUS_OK, PREVIEW_STATUS_UNAVAILABLE}:
        raise ValueError(
            f"{PREVIEW_UNION_CONTRACT_ERROR_CODE}: status must be '{PREVIEW_STATUS_OK}' or '{PREVIEW_STATUS_UNAVAILABLE}'."
        )

    doc_meta = _mapping(payload.get("doc_meta"))
    if not _text(doc_meta.get("document_id")):
        raise ValueError(f"{PREVIEW_UNION_CONTRACT_ERROR_CODE}: doc_meta.document_id is required.")

    reason_code = _text(payload.get("reason_code"))
    reason = _text(payload.get("reason"))
    if status == PREVIEW_STATUS_UNAVAILABLE and (not reason_code or not reason):
        raise ValueError(
            f"{PREVIEW_UNION_CONTRACT_ERROR_CODE}: unavailable payload requires reason_code and reason."
        )
    if status == PREVIEW_STATUS_OK and (reason_code or reason):
        raise ValueError(
            f"{PREVIEW_UNION_CONTRACT_ERROR_CODE}: ok payload must not set reason_code or reason."
        )

    page = _mapping(payload.get("page"))
    number = _int_value(page.get("number"))
    text = _text(page.get("text"))
    if number <= 0:
        raise ValueError(f"{PREVIEW_UNION_CONTRACT_ERROR_CODE}: page.number must be a positive integer.")
    if status == PREVIEW_STATUS_OK and not text:
        raise ValueError(f"{PREVIEW_UNION_CONTRACT_ERROR_CODE}: ok payload requires page.text.")

    normalized = {
        "doc_meta": {
            "checksum": _text(doc_meta.get("checksum")),
            "document_id": _text(doc_meta.get("document_id")),
            "page_count": _int_value(doc_meta.get("page_count")),
            "requested_page": _int_value(doc_meta.get("requested_page")),
            "source_name": _text(doc_meta.get("source_name")),
        },
        "fallback_snippet": _text(payload.get("fallback_snippet")),
        "highlights": _list_of_maps(payload.get("highlights")),
        "page": {
            "number": number,
            "text": text,
        },
        "pdf_url": _text(payload.get("pdf_url")),
        "reason": reason,
        "reason_code": reason_code,
        "status": status,
    }
    return normalized


def _mapping(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): value[key] for key in sorted(value.keys(), key=str)}


def _list_of_maps(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, object]] = []
    for item in value:
        if isinstance(item, Mapping):
            rows.append({str(key): item[key] for key in sorted(item.keys(), key=str)})
    return rows


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _int_value(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return 0


__all__ = [
    "PREVIEW_STATUS_OK",
    "PREVIEW_STATUS_UNAVAILABLE",
    "PREVIEW_UNAVAILABLE_REASON_NON_PDF",
    "PREVIEW_UNAVAILABLE_REASON_PAGE_TEXT",
    "PREVIEW_UNAVAILABLE_REASON_UNKNOWN",
    "PREVIEW_UNION_CONTRACT_ERROR_CODE",
    "build_preview_ok_payload",
    "build_preview_unavailable_payload",
    "validate_preview_union_payload",
]
