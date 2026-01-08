from pathlib import Path

from namel3ss.runtime.ui.explain.builder import build_ui_explain_pack
from namel3ss.runtime.ui.explain.render_plain import render_see


def _write_app(tmp_path: Path, content: str) -> Path:
    app_path = tmp_path / "app.ai"
    app_path.write_text(content, encoding="utf-8")
    return app_path


def test_chart_reasons_are_in_see_output(tmp_path: Path) -> None:
    app_path = _write_app(
        tmp_path,
        '''
spec is "1.0"
record "Metric":
  name text
  value number

page "home":
  table is "Metric"
  chart is "Metric":
    type is bar
    x is name
    y is value
    explain is "Value by name"
'''.lstrip(),
    )
    pack = build_ui_explain_pack(tmp_path, app_path.as_posix())
    text = render_see(pack)
    assert "chart" in text
    assert "type: bar" in text
    assert "mapping:" in text
    assert "explain: Value by name" in text
