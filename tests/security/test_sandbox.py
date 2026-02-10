from __future__ import annotations

import json
from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.security.audit import enforce_security_audit, run_security_audit


def _write_plugin(
    root: Path,
    *,
    name: str,
    renderer_code: str,
    permissions: list[str] | None = None,
) -> None:
    plugin_root = root / "plugins" / name
    plugin_root.mkdir(parents=True, exist_ok=True)
    payload = {
        "name": name,
        "module": "renderer.py",
        "permissions": permissions or ["ui"],
        "components": [
            {
                "name": "Widget",
                "props": {"label": "string"},
                "events": [],
            }
        ],
    }
    (plugin_root / "plugin.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (plugin_root / "renderer.py").write_text(renderer_code, encoding="utf-8")


def test_security_audit_flags_unsafe_plugin_renderer(tmp_path: Path) -> None:
    _write_plugin(
        tmp_path,
        name="unsafe_panel",
        renderer_code="def render(props, state):\n    return [build_node()]\n",
    )
    report = run_security_audit(
        project_root=tmp_path,
        plugin_names=("unsafe_panel",),
    )
    codes = [item.code for item in report.findings]
    assert "plugin_renderer_violation" in codes
    with pytest.raises(Namel3ssError):
        enforce_security_audit(report)


def test_security_audit_flags_translation_injection_token(tmp_path: Path) -> None:
    locales = tmp_path / "i18n" / "locales"
    locales.mkdir(parents=True, exist_ok=True)
    payload = {
        "locale": "en",
        "fallback_locale": "en",
        "messages": {
            "pages.0.title": {"en": "<script>alert('x')</script>"},
        },
    }
    (locales / "en.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    report = run_security_audit(project_root=tmp_path)
    assert [item.code for item in report.findings] == ["translation_injection_pattern"]


def test_security_audit_orders_findings_deterministically(tmp_path: Path) -> None:
    _write_plugin(
        tmp_path,
        name="legacy_panel",
        renderer_code='def render(props, state):\n    return [{"type": "text", "value": "ok"}]\n',
        permissions=["legacy_full_access"],
    )
    report = run_security_audit(
        project_root=tmp_path,
        plugin_names=("legacy_panel",),
        theme_overrides={
            "foreground_color": "javascript:evil()",
            "spacing_scale": {"bad": "value"},
        },
    )
    assert [item.code for item in report.findings] == [
        "theme_override_injection_pattern",
        "theme_override_type",
        "plugin_permission_legacy_full_access",
    ]
