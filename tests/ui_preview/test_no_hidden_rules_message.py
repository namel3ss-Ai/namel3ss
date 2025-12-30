from pathlib import Path

from namel3ss.runtime.ui.explain.builder import build_ui_explain_pack
from namel3ss.runtime.ui.explain.render_plain import render_see


def _write_app(tmp_path: Path, content: str) -> Path:
    app_path = tmp_path / "app.ai"
    app_path.write_text(content, encoding="utf-8")
    return app_path


def test_no_hidden_rules_message(tmp_path: Path) -> None:
    app_path = _write_app(
        tmp_path,
        """
page "home":
  title is "Hello"

spec is "1.0"

flow "demo":
  return "ok"
""".lstrip(),
    )
    pack = build_ui_explain_pack(tmp_path, app_path.as_posix())
    text = render_see(pack)
    assert "No explicit hidden rules were recorded for this ui." in text
