from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program


def _write_plugin(root: Path) -> None:
    plugin_dir = root / "timeline"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.yaml").write_text(
        (
            "name: timeline\n"
            "version: \"0.1.0\"\n"
            "permissions:\n"
            "  - ui\n"
            "hooks:\n"
            "  studio: hooks.py\n"
            "module: render.py\n"
            "components:\n"
            "  - name: TimelinePanel\n"
            "    props:\n"
            "      events: state_path\n"
        ),
        encoding="utf-8",
    )
    (plugin_dir / "render.py").write_text(
        "def render(props, state):\n    return [{\"type\": \"timeline_panel\"}]\n",
        encoding="utf-8",
    )
    (plugin_dir / "hooks.py").write_text(
        "def on_studio_load(context):\n    return {\"id\": \"timeline\", \"title\": \"Timeline\"}\n",
        encoding="utf-8",
    )


def test_plugin_hooks_are_ignored_without_hook_execution_capability(monkeypatch, tmp_path: Path) -> None:
    plugin_root = tmp_path / "ui_plugins"
    _write_plugin(plugin_root)
    monkeypatch.setenv("N3_UI_PLUGIN_DIRS", str(plugin_root))
    source = '''spec is "1.0"

capabilities:
  custom_ui
  sandbox
  extension_trust

use plugin "timeline"

page "home":
  TimelinePanel events: state.events
'''
    program = lower_ir_program(source)
    hook_manager = getattr(program, "extension_hook_manager", None)
    assert hook_manager is not None
    assert getattr(hook_manager, "has_hooks", True) is False


def test_plugin_permissions_require_extension_trust_capability(monkeypatch, tmp_path: Path) -> None:
    plugin_root = tmp_path / "ui_plugins"
    _write_plugin(plugin_root)
    monkeypatch.setenv("N3_UI_PLUGIN_DIRS", str(plugin_root))
    source = '''spec is "1.0"

capabilities:
  custom_ui
  sandbox
  extension_hooks

use plugin "timeline"

page "home":
  TimelinePanel events: state.events
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "extension_trust" in exc.value.message


def test_hook_execution_capability_loads_studio_hooks(monkeypatch, tmp_path: Path) -> None:
    plugin_root = tmp_path / "ui_plugins"
    _write_plugin(plugin_root)
    monkeypatch.setenv("N3_UI_PLUGIN_DIRS", str(plugin_root))
    source = '''spec is "1.0"

capabilities:
  custom_ui
  sandbox
  extension_trust
  hook_execution

use plugin "timeline"

page "home":
  TimelinePanel events: state.events
'''
    program = lower_ir_program(source)
    hook_manager = getattr(program, "extension_hook_manager", None)
    assert hook_manager is not None
    assert hook_manager.has_hooks is True
