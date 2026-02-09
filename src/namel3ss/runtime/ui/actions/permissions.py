from __future__ import annotations

from namel3ss.runtime.app_permissions_engine import require_permission


_ACTION_PERMISSION_MAP: dict[str, str] = {
    "open_page": "navigation.change_page",
    "go_back": "navigation.change_page",
    "retrieval_run": "uploads.read",
    "upload_select": "uploads.write",
    "upload_clear": "uploads.write",
    "upload_replace": "uploads.write",
    "ingestion_run": "uploads.write",
    "ingestion_review": "uploads.write",
    "ingestion_skip": "uploads.write",
}


def enforce_action_permission(
    program_ir,
    *,
    action_type: str,
    line: int | None = None,
    column: int | None = None,
) -> None:
    permission = _ACTION_PERMISSION_MAP.get(str(action_type or ""))
    if permission is None:
        return
    require_permission(
        permission,
        permissions=getattr(program_ir, "app_permissions", None),
        enabled=bool(getattr(program_ir, "app_permissions_enabled", False)),
        line=line,
        column=column,
        reason=f"ui action '{action_type}'",
    )


__all__ = ["enforce_action_permission"]
