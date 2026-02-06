from __future__ import annotations

from pathlib import Path

from namel3ss.errors.contract import build_error_entry
from namel3ss.errors.base import Namel3ssError


DEFAULT_REMEDIATION = "Check the request and try again."


def build_error_envelope(
    *,
    error: Exception | None,
    error_payload: dict | None = None,
    error_pack: dict | None = None,
    project_root: str | Path | None = None,
) -> dict:
    entry = build_error_entry(
        error=error,
        error_payload=error_payload,
        error_pack=error_pack,
        project_root=project_root,
    )
    code = entry.get("code") if isinstance(entry, dict) else None
    message = entry.get("message") if isinstance(entry, dict) else None
    remediation = entry.get("remediation") if isinstance(entry, dict) else None
    if not code:
        code = "runtime_error"
    if not message:
        if isinstance(error, Namel3ssError):
            message = error.message
        else:
            message = "Runtime error."
    if not remediation:
        remediation = DEFAULT_REMEDIATION
    return {
        "code": str(code),
        "message": str(message),
        "remediation": str(remediation),
    }


__all__ = ["DEFAULT_REMEDIATION", "build_error_envelope"]
