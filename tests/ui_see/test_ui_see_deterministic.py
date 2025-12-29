from pathlib import Path

from namel3ss.runtime.ui.explain.builder import build_ui_explain_pack
from namel3ss.runtime.ui.explain.render_plain import render_see


def _write_app(tmp_path: Path, content: str) -> Path:
    app_path = tmp_path / "app.ai"
    app_path.write_text(content, encoding="utf-8")
    return app_path


def test_render_is_deterministic(tmp_path: Path) -> None:
    app_path = _write_app(
        tmp_path,
        """
page "home":
  title is "Hello"
  text is "Welcome"

flow "demo":
  return "ok"
""".lstrip(),
    )
    pack = build_ui_explain_pack(tmp_path, app_path.as_posix())
    text_one = render_see(pack)
    text_two = render_see(pack)
    assert text_one == text_two
