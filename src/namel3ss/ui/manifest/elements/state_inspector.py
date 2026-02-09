from __future__ import annotations

from typing import Any

from namel3ss.ui.manifest.canonical import _element_id


def inject_state_inspector_elements(
    manifest: dict,
    *,
    persistence_backend: object,
    migration_status: object,
    state_schema_version: object,
) -> dict:
    if not isinstance(manifest, dict):
        return manifest
    pages = manifest.get("pages")
    if not isinstance(pages, list):
        return manifest
    backend = _sanitize(persistence_backend) if isinstance(persistence_backend, dict) else {}
    status = _sanitize(migration_status) if isinstance(migration_status, dict) else {}
    schema_version = str(state_schema_version or "").strip()
    if not backend and not status and not schema_version:
        return manifest
    for page in pages:
        if not isinstance(page, dict):
            continue
        page_slug = str(page.get("slug") or page.get("name") or "page")
        page_name = str(page.get("name") or page_slug)
        element = _state_inspector_element(
            page_name=page_name,
            page_slug=page_slug,
            persistence_backend=backend,
            migration_status=status,
            state_schema_version=schema_version,
        )
        if isinstance(page.get("layout"), dict):
            layout = page["layout"]
            main_items = layout.get("main")
            if not isinstance(main_items, list):
                main_items = []
            layout["main"] = _inject_element(main_items, element)
            continue
        elements = page.get("elements")
        if not isinstance(elements, list):
            elements = []
            page["elements"] = elements
        page["elements"] = _inject_element(elements, element)
    if backend:
        manifest["persistence_backend"] = backend
    if status:
        manifest["migration_status"] = status
    if schema_version:
        manifest["state_schema_version"] = schema_version
    return manifest


def _inject_element(items: list[dict], element: dict[str, Any]) -> list[dict]:
    filtered = [entry for entry in items if not _is_state_inspector(entry)]
    if filtered and isinstance(filtered[0], dict) and filtered[0].get("type") == "runtime_error":
        return [filtered[0], element, *filtered[1:]]
    return [element, *filtered]


def _state_inspector_element(
    *,
    page_name: str,
    page_slug: str,
    persistence_backend: dict[str, Any],
    migration_status: dict[str, Any],
    state_schema_version: str,
) -> dict[str, Any]:
    return {
        "type": "state_inspector",
        "element_id": _element_id(page_slug, "state_inspector", [0]),
        "page": page_name,
        "page_slug": page_slug,
        "index": 0,
        "line": 0,
        "column": 0,
        "source": "runtime.persistence",
        "persistence_backend": persistence_backend,
        "migration_status": migration_status,
        "state_schema_version": state_schema_version,
    }


def _is_state_inspector(entry: object) -> bool:
    return isinstance(entry, dict) and entry.get("type") == "state_inspector"


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(value[key]) for key in sorted(value.keys(), key=str)}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, str)) or value is None:
        return value
    return str(value)


__all__ = ["inject_state_inspector_elements"]
