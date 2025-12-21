from __future__ import annotations

from typing import Any, Dict, Optional

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.render import format_error


def build_error_payload(
    message: str,
    *,
    kind: str = "unknown",
    err: Optional[Namel3ssError] = None,
    details: Optional[dict] = None,
    source: Optional[str] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"ok": False, "error": message, "kind": kind}
    if err:
        if err.line is not None:
            payload["location"] = {"line": err.line, "column": err.column}
        err_details = getattr(err, "details", None)
        if err_details:
            payload["details"] = err_details
    if details:
        payload["details"] = details
    return payload


def build_error_from_exception(
    err: Namel3ssError,
    *,
    kind: str = "unknown",
    source: Optional[str] = None,
    details: Optional[dict] = None,
) -> Dict[str, Any]:
    message = format_error(err, source)
    return build_error_payload(message, kind=kind, err=err, details=details, source=source)
