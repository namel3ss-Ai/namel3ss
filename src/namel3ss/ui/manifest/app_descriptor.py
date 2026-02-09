from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from namel3ss.ir.model.ui_state import UI_STATE_SCOPES
from namel3ss.runtime.app_permissions_engine import KNOWN_APP_PERMISSIONS
from namel3ss.version import get_version


APP_DESCRIPTOR_SCHEMA = "app_descriptor.v1"


def build_app_descriptor(
    program,
    manifest: dict,
    *,
    app_path: str | Path,
) -> dict[str, object]:
    app_file = Path(app_path)
    pages = _page_names(manifest)
    capabilities = _capabilities(program)
    permissions = _permissions(program)
    ui_state_schema = _ui_state_schema(program)
    return {
        "schema": APP_DESCRIPTOR_SCHEMA,
        "archive": {
            "format": "n3a.v1",
            "entrypoint": "compiled_ir.json",
        },
        "app": {
            "name": app_file.stem,
            "source": app_file.name,
        },
        "language_spec_version": str(getattr(program, "spec_version", "") or ""),
        "namel3ss_version": get_version(),
        "capabilities": capabilities,
        "permissions": permissions,
        "pages": pages,
        "ui_state": ui_state_schema,
        "runtime_config": {
            "default_mode": "production",
            "supported_modes": ["production", "studio"],
        },
        "static_assets": [],
    }


def _capabilities(program) -> list[str]:
    values = getattr(program, "capabilities", ()) or ()
    unique = {str(item).strip().lower() for item in values if isinstance(item, str) and str(item).strip()}
    return sorted(unique)


def _permissions(program) -> dict[str, bool]:
    raw = getattr(program, "app_permissions", None)
    enabled = bool(getattr(program, "app_permissions_enabled", False))
    matrix = raw if isinstance(raw, dict) else {}
    if not enabled:
        return {key: True for key in KNOWN_APP_PERMISSIONS}
    return {key: bool(matrix.get(key, False)) for key in KNOWN_APP_PERMISSIONS}


def _ui_state_schema(program) -> dict[str, list[dict[str, object]]]:
    declaration = getattr(program, "ui_state", None)
    if declaration is None:
        return {}
    payload: dict[str, list[dict[str, object]]] = {}
    for scope in UI_STATE_SCOPES:
        fields = getattr(declaration, scope, None) or []
        rows: list[dict[str, object]] = []
        for field in fields:
            key = str(getattr(field, "key", "") or "")
            if not key:
                continue
            rows.append(
                {
                    "key": key,
                    "type": str(getattr(field, "type_name", "") or ""),
                    "default": deepcopy(getattr(field, "default_value", None)),
                }
            )
        if rows:
            payload[scope] = rows
    return payload


def _page_names(manifest: dict) -> list[str]:
    pages = manifest.get("pages") if isinstance(manifest, dict) else None
    if not isinstance(pages, list):
        return []
    names: list[str] = []
    for page in pages:
        if not isinstance(page, dict):
            continue
        name = page.get("name")
        if isinstance(name, str) and name:
            names.append(name)
    return names


__all__ = ["APP_DESCRIPTOR_SCHEMA", "build_app_descriptor"]
