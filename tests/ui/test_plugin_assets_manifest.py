from __future__ import annotations

from dataclasses import dataclass

from namel3ss.ui.manifest.plugin_assets import build_plugin_assets_manifest


@dataclass(frozen=True)
class _Schema:
    name: str
    version: str
    asset_js: tuple[str, ...]
    asset_css: tuple[str, ...]


@dataclass(frozen=True)
class _Registry:
    plugin_schemas: tuple[_Schema, ...]


def test_build_plugin_assets_manifest_returns_deterministic_urls() -> None:
    registry = _Registry(
        plugin_schemas=(
            _Schema(
                name="charts",
                version="0.1.0",
                asset_js=("assets/runtime.js",),
                asset_css=("assets/style.css",),
            ),
        )
    )
    payload = build_plugin_assets_manifest(registry)
    assert payload == [
        {
            "name": "charts",
            "version": "0.1.0",
            "assets": {
                "js": ["/api/plugins/charts/assets/js/assets/runtime.js"],
                "css": ["/api/plugins/charts/assets/css/assets/style.css"],
            },
        }
    ]
