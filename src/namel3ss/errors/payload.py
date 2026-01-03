from __future__ import annotations

from typing import Any, Dict, Optional

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.contract import build_error_entry
from namel3ss.errors.render import format_error


def build_error_payload(
    message: str,
    *,
    kind: str = "unknown",
    err: Optional[Namel3ssError] = None,
    details: Optional[dict] = None,
    source: Optional[str] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"ok": False, "error": message, "message": message, "kind": kind}
    if err:
        if err.line is not None:
            payload["location"] = {"line": err.line, "column": err.column}
        err_details = getattr(err, "details", None)
        if err_details:
            payload["details"] = err_details
    if details:
        payload["details"] = details
    entry = build_error_entry(error=err, error_payload=payload, error_pack=None)
    if entry:
        payload["error_entry"] = entry
        payload["errors"] = [entry]
    return payload


def build_error_from_exception(
    err: Namel3ssError,
    *,
    kind: str = "unknown",
    source: Optional[str] = None,
    details: Optional[dict] = None,
) -> Dict[str, Any]:
    message = err.message
    resolved_kind = kind
    if err.details and isinstance(err.details, dict):
        category = err.details.get("category")
        if isinstance(category, str) and category:
            resolved_kind = category
    payload = build_error_payload(message, kind=resolved_kind, err=err, details=details, source=source)
    payload["error"] = format_error(err, source)
    return payload
