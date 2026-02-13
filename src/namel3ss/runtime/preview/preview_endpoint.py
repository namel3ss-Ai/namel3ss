from __future__ import annotations

from collections.abc import Mapping

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.runtime.backend.document_handler import handle_document_page
from namel3ss.runtime.preview.preview_contract import (
    PREVIEW_UNAVAILABLE_REASON_NON_PDF,
    PREVIEW_UNAVAILABLE_REASON_PAGE_TEXT,
    PREVIEW_UNAVAILABLE_REASON_UNKNOWN,
    PREVIEW_UNION_CONTRACT_ERROR_CODE,
    build_preview_ok_payload,
    build_preview_unavailable_payload,
    validate_preview_union_payload,
)


def handle_preview_page_request(
    ctx,
    *,
    document_id: str,
    page_number: object,
    state: dict | None,
    chunk_id: str | None,
    citation_id: str | None,
    identity: dict | None,
    policy_decl: object | None,
) -> tuple[dict[str, object], int]:
    try:
        page_payload = handle_document_page(
            ctx,
            document_id=document_id,
            page_number=page_number,
            state=state,
            chunk_id=chunk_id,
            citation_id=citation_id,
            identity=identity,
            policy_decl=policy_decl,
        )
        normalized = validate_preview_union_payload(build_preview_ok_payload(page_payload))
        return normalized, 200
    except Namel3ssError as err:
        unavailable = _unavailable_reason(err)
        if unavailable is not None:
            reason_code, reason_text = unavailable
            unavailable_payload = build_preview_unavailable_payload(
                document_id=document_id,
                page_number=page_number,
                reason_code=reason_code,
                reason=reason_text,
                fallback_snippet=_fallback_snippet(state, document_id),
                source_name=_source_name(state, document_id),
                page_count=_page_count(state, document_id),
                checksum=_checksum(state, document_id),
            )
            normalized = validate_preview_union_payload(unavailable_payload)
            return normalized, 200
        payload = build_error_from_exception(err, kind="engine")
        payload["error_code"] = _error_code_for_error(err)
        return payload, 400
    except ValueError as err:
        payload = build_error_payload(str(err), kind="engine")
        payload["error_code"] = PREVIEW_UNION_CONTRACT_ERROR_CODE
        return payload, 500
    except Exception as err:  # pragma: no cover - defensive guard rail
        payload = build_error_payload(str(err), kind="internal")
        payload["error_code"] = "runtime.preview_internal"
        return payload, 500


def _unavailable_reason(err: Namel3ssError) -> tuple[str, str] | None:
    message = str(err).strip()
    lowered = message.lower()
    if "is not a pdf document" in lowered:
        return PREVIEW_UNAVAILABLE_REASON_NON_PDF, _first_line(message)
    if "page text for" in lowered:
        return PREVIEW_UNAVAILABLE_REASON_PAGE_TEXT, _first_line(message)
    return None


def _first_line(value: str) -> str:
    if not value:
        return ""
    return value.splitlines()[0].strip()


def _error_code_for_error(err: Namel3ssError) -> str:
    details = getattr(err, "details", None)
    if isinstance(details, Mapping):
        code = details.get("error_code")
        if isinstance(code, str) and code.strip():
            return code.strip()
    return "runtime.preview_request_failed"


def _ingestion_report(state: dict | None, document_id: str) -> dict[str, object]:
    if not isinstance(state, Mapping):
        return {}
    ingestion = state.get("ingestion")
    if not isinstance(ingestion, Mapping):
        return {}
    report = ingestion.get(document_id)
    if not isinstance(report, Mapping):
        return {}
    return {str(key): report[key] for key in sorted(report.keys(), key=str)}


def _fallback_snippet(state: dict | None, document_id: str) -> str:
    report = _ingestion_report(state, document_id)
    preview = report.get("preview")
    if isinstance(preview, str) and preview.strip():
        return preview.strip()[:240]
    page_text = report.get("page_text")
    if isinstance(page_text, list):
        for item in page_text:
            if isinstance(item, str) and item.strip():
                return item.strip()[:240]
    return ""


def _source_name(state: dict | None, document_id: str) -> str:
    report = _ingestion_report(state, document_id)
    provenance = report.get("provenance")
    if isinstance(provenance, Mapping):
        value = provenance.get("source_name")
        if isinstance(value, str):
            return value.strip()
    return ""


def _page_count(state: dict | None, document_id: str) -> int:
    report = _ingestion_report(state, document_id)
    page_text = report.get("page_text")
    if isinstance(page_text, list):
        return len(page_text)
    return 0


def _checksum(state: dict | None, document_id: str) -> str:
    report = _ingestion_report(state, document_id)
    provenance = report.get("provenance")
    if isinstance(provenance, Mapping):
        value = provenance.get("document_id")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return document_id.strip()


__all__ = ["handle_preview_page_request"]
