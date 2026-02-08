from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.ui.plugins.schema import parse_plugin_manifest


def test_manifest_parses_extension_metadata(tmp_path: Path) -> None:
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "runtime.js").write_text("console.log('ready');\n", encoding="utf-8")
    (assets_dir / "style.css").write_text(".widget { color: #111; }\n", encoding="utf-8")
    payload = {
        "name": "timeline-panel",
        "version": "0.1.0",
        "author": "ACME Labs",
        "description": "Studio timeline view",
        "permissions": ["ui", "memory:read"],
        "hooks": {"studio": "timeline/hooks.py"},
        "min_api_version": 1,
        "signature": "abc123",
        "tags": ["studio", "debug"],
        "rating": 4.5,
        "module": "renderer.py",
        "asset_js": "assets/runtime.js",
        "asset_css": "assets/style.css",
        "components": [
            {
                "name": "TimelineWidget",
                "props": {"events": "state_path"},
            }
        ],
    }
    schema = parse_plugin_manifest(payload, source_path=tmp_path / "plugin.yaml", plugin_root=tmp_path)
    assert schema.name == "timeline-panel"
    assert schema.permissions == ("ui", "memory:read")
    assert dict(schema.hooks) == {"studio": "timeline/hooks.py"}
    assert schema.min_api_version == 1
    assert schema.signature == "abc123"
    assert schema.tags == ("studio", "debug")
    assert schema.rating == 4.5
    assert schema.asset_js == ("assets/runtime.js",)
    assert schema.asset_css == ("assets/style.css",)


def test_manifest_rejects_unknown_permission(tmp_path: Path) -> None:
    payload = {
        "name": "bad",
        "module": "render.py",
        "permissions": ["ui", "kernel:root"],
        "components": [{"name": "Widget", "props": {}}],
    }
    with pytest.raises(Namel3ssError) as exc:
        parse_plugin_manifest(payload, source_path=tmp_path / "plugin.yaml", plugin_root=tmp_path)
    assert "permissions" in exc.value.message
    assert "kernel:root" in exc.value.message


def test_manifest_requires_component_or_hook(tmp_path: Path) -> None:
    payload = {
        "name": "empty",
        "version": "0.1.0",
    }
    with pytest.raises(Namel3ssError) as exc:
        parse_plugin_manifest(payload, source_path=tmp_path / "plugin.yaml", plugin_root=tmp_path)
    assert "at least one component or one hook" in exc.value.message


def test_manifest_rejects_newer_api_version(tmp_path: Path) -> None:
    payload = {
        "name": "future",
        "module": "render.py",
        "min_api_version": 999,
        "components": [{"name": "Widget", "props": {}}],
    }
    with pytest.raises(Namel3ssError) as exc:
        parse_plugin_manifest(payload, source_path=tmp_path / "plugin.yaml", plugin_root=tmp_path)
    assert "min_api_version" in exc.value.message


def test_manifest_rejects_missing_asset_file(tmp_path: Path) -> None:
    payload = {
        "name": "asset-missing",
        "module": "render.py",
        "asset_js": "assets/runtime.js",
        "components": [{"name": "Widget", "props": {}}],
    }
    with pytest.raises(Namel3ssError) as exc:
        parse_plugin_manifest(payload, source_path=tmp_path / "plugin.yaml", plugin_root=tmp_path)
    assert "asset_js" in exc.value.message
