from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


def _write_plugin(root: Path, name: str, manifest: str, module_source: str) -> None:
    plugin_dir = root / name
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.yaml").write_text(manifest.strip() + "\n", encoding="utf-8")
    (plugin_dir / "render.py").write_text(module_source.strip() + "\n", encoding="utf-8")


def test_custom_component_plugin_renders_manifest(monkeypatch, tmp_path: Path) -> None:
    plugin_root = tmp_path / "ui_plugins"
    _write_plugin(
        plugin_root,
        "maps",
        """
name: maps
module: render.py
components:
  - name: MapViewer
    props:
      lat: state_path
      lng: state_path
      zoom:
        type: number
        required: false
    events:
      - onClick
""",
        """
def render(props, state):
    return [{
        "type": "map_viewer",
        "lat": props["lat"],
        "lng": props["lng"],
        "zoom": props["zoom"] if "zoom" in props else 10,
        "user_role": state["user"]["role"],
    }]
""",
    )
    monkeypatch.setenv("N3_UI_PLUGIN_DIRS", str(plugin_root))

    source = '''spec is "1.0"

capabilities:
  custom_ui
  sandbox

use plugin "maps"

flow "OpenLocationDetails":
  return "ok"

page "Dashboard":
  MapViewer lat: state.user.location.lat lng: state.user.location.lng zoom: 12 onClick: OpenLocationDetails
'''
    program = lower_ir_program(source)
    manifest = build_manifest(
        program,
        state={
            "user": {
                "role": "admin",
                "location": {"lat": 1.234, "lng": 5.678},
            }
        },
        store=None,
    )

    element = manifest["pages"][0]["elements"][0]
    assert element["type"] == "custom_component"
    assert element["component"] == "MapViewer"
    assert element["plugin"] == "maps"
    assert element["nodes"][0]["type"] == "map_viewer"
    assert element["nodes"][0]["user_role"] == "admin"

    second = build_manifest(
        program,
        state={
            "user": {
                "role": "admin",
                "location": {"lat": 1.234, "lng": 5.678},
            }
        },
        store=None,
    )
    assert manifest == second


def test_unknown_custom_component_requires_plugin() -> None:
    source = '''spec is "1.0"

page "home":
  FancyWidget label: "Hello"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "Component FancyWidget is not defined. Did you forget to use plugin?" in exc.value.message


def test_custom_component_validates_props(monkeypatch, tmp_path: Path) -> None:
    plugin_root = tmp_path / "ui_plugins"
    _write_plugin(
        plugin_root,
        "charts",
        """
name: charts
module: render.py
components:
  - name: LineChart
    props:
      data: state_path
      x_field: string
      y_field: string
""",
        """
def render(props, state):
    return [{"type": "line_chart", "props": props}]
""",
    )
    monkeypatch.setenv("N3_UI_PLUGIN_DIRS", str(plugin_root))

    source = '''spec is "1.0"

capabilities:
  custom_ui
  sandbox

use plugin "charts"

page "home":
  LineChart data: state.metrics.records x_field: "month" y_field: "revenue" unknown: "x"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "Unknown property 'unknown' on component 'LineChart'." in exc.value.message


def test_plugin_sandbox_rejects_function_calls(monkeypatch, tmp_path: Path) -> None:
    plugin_root = tmp_path / "ui_plugins"
    _write_plugin(
        plugin_root,
        "unsafe",
        """
name: unsafe
module: render.py
components:
  - name: UnsafeWidget
    props:
      label: string
""",
        """
def render(props, state):
    return [{"type": "unsafe", "label": str(props["label"])}]
""",
    )
    monkeypatch.setenv("N3_UI_PLUGIN_DIRS", str(plugin_root))

    source = '''spec is "1.0"

capabilities:
  custom_ui
  sandbox

use plugin "unsafe"

page "home":
  UnsafeWidget label: "x"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "cannot call functions inside render()" in exc.value.message
