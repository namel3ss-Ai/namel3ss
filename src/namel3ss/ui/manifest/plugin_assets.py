from __future__ import annotations

from typing import Any


def build_plugin_assets_manifest(ui_plugin_registry: object) -> list[dict]:
    schemas = tuple(getattr(ui_plugin_registry, "plugin_schemas", ()) or ())
    if not schemas:
        return []
    entries: list[dict] = []
    for schema in schemas:
        name = str(getattr(schema, "name", "") or "").strip()
        if not name:
            continue
        js_assets = tuple(getattr(schema, "asset_js", ()) or ())
        css_assets = tuple(getattr(schema, "asset_css", ()) or ())
        if not js_assets and not css_assets:
            continue
        version = str(getattr(schema, "version", "0.1.0") or "0.1.0")
        entry: dict[str, Any] = {
            "name": name,
            "version": version,
            "assets": {
                "js": [_asset_url(name, "js", rel) for rel in js_assets],
                "css": [_asset_url(name, "css", rel) for rel in css_assets],
            },
        }
        entries.append(entry)
    return entries


def _asset_url(plugin_name: str, asset_type: str, relative_path: object) -> str:
    path = str(relative_path or "").strip().lstrip("/")
    return f"/api/plugins/{plugin_name}/assets/{asset_type}/{path}"


__all__ = ["build_plugin_assets_manifest"]
