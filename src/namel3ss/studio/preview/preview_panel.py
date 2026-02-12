from __future__ import annotations

from collections.abc import Mapping

from namel3ss.runtime.preview.preview_contract import (
    PREVIEW_STATUS_OK,
    PREVIEW_STATUS_UNAVAILABLE,
    PREVIEW_UNION_CONTRACT_ERROR_CODE,
    validate_preview_union_payload,
)


def render_preview_panel(payload: Mapping[str, object]) -> dict[str, object]:
    try:
        normalized = validate_preview_union_payload(payload)
    except ValueError as exc:
        raise ValueError(f"{PREVIEW_UNION_CONTRACT_ERROR_CODE}: {exc}") from exc

    status = normalized["status"]
    doc_meta = normalized["doc_meta"]
    page = normalized["page"]
    if status == PREVIEW_STATUS_OK:
        return {
            "doc_meta": doc_meta,
            "highlights": normalized["highlights"],
            "panel": {
                "message": "",
                "mode": PREVIEW_STATUS_OK,
                "page_number": page["number"],
                "page_text": page["text"],
                "reason": "",
                "reason_code": "",
            },
            "pdf_url": normalized["pdf_url"],
        }

    assert status == PREVIEW_STATUS_UNAVAILABLE
    message = normalized["reason"] or "Preview unavailable."
    snippet = normalized["fallback_snippet"]
    if snippet:
        message = f"{message}\n\nFallback snippet:\n{snippet}"
    return {
        "doc_meta": doc_meta,
        "highlights": [],
        "panel": {
            "message": message,
            "mode": PREVIEW_STATUS_UNAVAILABLE,
            "page_number": page["number"],
            "page_text": "",
            "reason": normalized["reason"],
            "reason_code": normalized["reason_code"],
        },
        "pdf_url": normalized["pdf_url"],
    }


__all__ = ["render_preview_panel"]
