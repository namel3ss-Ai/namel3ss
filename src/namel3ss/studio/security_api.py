from __future__ import annotations

from pathlib import Path

from namel3ss.governance.audit import list_audit_entries, summarize_status
from namel3ss.runtime.security.compliance_status import build_security_status


def get_security_payload(app_path: str) -> dict[str, object]:
    app_file = Path(app_path)
    payload = build_security_status(app_file.parent, app_file)
    payload["app_path"] = app_file.as_posix()
    return payload


def get_audit_logs_payload(
    app_path: str,
    *,
    user: str | None,
    action: str | None,
    limit: int,
    offset: int,
) -> dict[str, object]:
    app_file = Path(app_path)
    entries = list_audit_entries(
        app_file.parent,
        app_file,
        user=_text(user) or None,
        action=_text(action) or None,
    )
    start = max(0, int(offset))
    size = max(1, int(limit))
    selected = entries[start : start + size]
    return {
        "ok": True,
        "count": len(selected),
        "total_count": len(entries),
        "offset": start,
        "limit": size,
        "entries": selected,
        "status": summarize_status(entries),
    }


def _text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


__all__ = ["get_audit_logs_payload", "get_security_payload"]
