from __future__ import annotations


def build_app_permissions_payload(program) -> dict | None:
    enabled = bool(getattr(program, "app_permissions_enabled", False))
    raw_permissions = getattr(program, "app_permissions", None)
    if not enabled or not isinstance(raw_permissions, dict):
        return None

    permissions = {
        key: bool(raw_permissions.get(key, False))
        for key in sorted((key for key in raw_permissions.keys() if isinstance(key, str)), key=str)
    }
    usage = _normalize_usage(getattr(program, "app_permissions_usage", None))
    warnings = _normalize_warnings(getattr(program, "app_permissions_warnings", None))

    payload: dict = {"permissions": permissions}
    inspector: dict[str, object] = {
        "enabled": True,
        "mode": "explicit",
    }
    if usage:
        inspector["usage"] = usage
    if warnings:
        inspector["warnings"] = warnings
    payload["inspector"] = inspector
    return payload


def _normalize_usage(raw: object) -> list[dict]:
    if not isinstance(raw, list):
        return []
    rows: list[dict] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        permission = entry.get("permission")
        reason = entry.get("reason")
        if not isinstance(permission, str) or not permission:
            continue
        if not isinstance(reason, str) or not reason:
            continue
        line = entry.get("line") if isinstance(entry.get("line"), int) else None
        column = entry.get("column") if isinstance(entry.get("column"), int) else None
        rows.append(
            {
                "permission": permission,
                "reason": reason,
                "line": line,
                "column": column,
            }
        )
    rows.sort(key=lambda item: (item["permission"], item["reason"], -1 if item["line"] is None else item["line"], -1 if item["column"] is None else item["column"]))
    return rows


def _normalize_warnings(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    warnings = [str(item).strip() for item in raw if isinstance(item, str) and str(item).strip()]
    return sorted(set(warnings))


__all__ = ["build_app_permissions_payload"]
