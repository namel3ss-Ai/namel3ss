from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program


def _write_plugin(root: Path) -> None:
    plugin_dir = root / "charts"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.yaml").write_text(
        (
            "name: charts\n"
            "module: render.py\n"
            "components:\n"
            "  - name: LineChart\n"
            "    props:\n"
            "      data: state_path\n"
            "      x_field: string\n"
            "      y_field: string\n"
        ),
        encoding="utf-8",
    )
    (plugin_dir / "render.py").write_text(
        "def render(props, state):\n    return [{\"type\": \"line_chart\", \"props\": props}]\n",
        encoding="utf-8",
    )


def test_plugins_require_sandbox_capability(monkeypatch, tmp_path: Path) -> None:
    plugin_root = tmp_path / "ui_plugins"
    _write_plugin(plugin_root)
    monkeypatch.setenv("N3_UI_PLUGIN_DIRS", str(plugin_root))

    source = '''spec is "1.0"

capabilities:
  custom_ui

use plugin "charts"

page "home":
  LineChart data: state.metrics.records x_field: "month" y_field: "revenue"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "sandbox" in exc.value.message
