from __future__ import annotations

from typing import Any

from namel3ss.ingestion.diagnostics import canonical_reason_codes
from namel3ss.ir import nodes as ir
from namel3ss.ui.manifest.canonical import _element_id
from namel3ss.ui.manifest.origin import _attach_origin
from namel3ss.ui.manifest.state_defaults import StateContext

from .base import _base_element


def build_ingestion_status_element(
    item: ir.UploadItem,
    *,
    upload_element: dict,
    page_name: str,
    page_slug: str,
    path: list[int],
    state_ctx: StateContext,
) -> dict | None:
    upload_name = str(getattr(item, "name", "") or "")
    if not upload_name:
        return None
    upload_ids = _selected_upload_ids(state_ctx.state, upload_name)
    upload_id, report = _select_ingestion_report(state_ctx.state, upload_ids)
    if upload_id is None or report is None:
        return None

    status = _normalize_status(report.get("status"))
    reasons = canonical_reason_codes(_normalize_reasons(report.get("reasons")))
    details = _normalize_reason_details(report.get("reason_details"), reasons)

    element_id = _status_element_id(upload_element, page_slug, path)
    index = _int_value(upload_element.get("index"), default=path[-1] if path else 0)
    base = _base_element(element_id, page_name, page_slug, index, item)
    source = f"state.ingestion.{upload_id}" if upload_id else "state.ingestion"

    element = {
        "type": "ingestion_status",
        "status": status,
        "reasons": reasons,
        "details": details,
        "source": source,
        "upload_name": upload_name,
        "upload_id": upload_id,
        **base,
    }
    fallback_used = report.get("fallback_used")
    if isinstance(fallback_used, str) and fallback_used:
        element["fallback_used"] = fallback_used
    return _attach_origin(element, item)


def _status_element_id(upload_element: dict, page_slug: str, path: list[int]) -> str:
    source_id = upload_element.get("element_id")
    if isinstance(source_id, str) and source_id:
        return f"{source_id}.ingestion_status"
    return _element_id(page_slug, "ingestion_status", path)


def _selected_upload_ids(state: dict, upload_name: str) -> list[str]:
    if not isinstance(state, dict):
        return []
    uploads = state.get("uploads")
    if not isinstance(uploads, dict):
        return []
    raw = uploads.get(upload_name)
    entries = _normalize_upload_entries(raw)
    ids = {
        str(identifier).strip()
        for identifier in (_entry_id(entry) for entry in entries)
        if isinstance(identifier, str) and identifier.strip()
    }
    return sorted(ids)


def _normalize_upload_entries(raw: object) -> list[dict]:
    if isinstance(raw, dict):
        if _looks_like_upload_entry(raw):
            return [raw]
        return [entry for entry in raw.values() if isinstance(entry, dict)]
    if isinstance(raw, list):
        return [entry for entry in raw if isinstance(entry, dict)]
    return []


def _looks_like_upload_entry(value: dict) -> bool:
    identifier = _entry_id(value)
    name = value.get("name")
    return isinstance(identifier, str) and bool(identifier) and isinstance(name, str) and bool(name)


def _entry_id(value: dict) -> str | None:
    candidate = value.get("id")
    if isinstance(candidate, str) and candidate:
        return candidate
    candidate = value.get("checksum")
    if isinstance(candidate, str) and candidate:
        return candidate
    return None


def _select_ingestion_report(state: dict, upload_ids: list[str]) -> tuple[str | None, dict | None]:
    ingestion = state.get("ingestion") if isinstance(state, dict) else None
    if not isinstance(ingestion, dict):
        return None, None
    candidates: list[tuple[int, str, dict]] = []
    for upload_id in upload_ids:
        report = ingestion.get(upload_id)
        if not isinstance(report, dict):
            continue
        status = _normalize_status(report.get("status"))
        candidates.append((_status_rank(status), upload_id, report))
    if not candidates:
        return None, None
    candidates.sort(key=lambda item: (-item[0], item[1]))
    _, upload_id, report = candidates[0]
    return upload_id, report


def _status_rank(status: str) -> int:
    if status == "block":
        return 2
    if status == "warn":
        return 1
    return 0


def _normalize_status(value: object) -> str:
    if value in {"pass", "warn", "block"}:
        return str(value)
    return "pass"


def _normalize_reasons(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _normalize_reason_details(value: object, reasons: list[str]) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    indexed: dict[str, dict[str, str]] = {}
    ordered_unknown: list[dict[str, str]] = []
    for entry in value:
        normalized = _normalize_reason_detail_entry(entry)
        if normalized is None:
            continue
        code = normalized["code"]
        if code in reasons:
            indexed.setdefault(code, normalized)
        else:
            ordered_unknown.append(normalized)
    ordered = [indexed[code] for code in reasons if code in indexed]
    ordered.extend(sorted(ordered_unknown, key=lambda item: item["code"]))
    return ordered


def _normalize_reason_detail_entry(value: Any) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    code = value.get("code")
    message = value.get("message")
    remediation = value.get("remediation")
    if not isinstance(code, str) or not code:
        return None
    if not isinstance(message, str):
        return None
    if not isinstance(remediation, str):
        return None
    return {
        "code": code,
        "message": message,
        "remediation": remediation,
    }


def _int_value(value: object, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    return default


__all__ = ["build_ingestion_status_element"]
