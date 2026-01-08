from pathlib import Path

from namel3ss.runtime.ui.explain.builder import build_ui_explain_pack
from namel3ss.runtime.ui.explain.render_plain import render_see


def _write_app(tmp_path: Path, content: str) -> Path:
    app_path = tmp_path / "app.ai"
    app_path.write_text(content, encoding="utf-8")
    return app_path


def test_ui_pack_origin_reason_in_see_output(tmp_path: Path) -> None:
    app_path = _write_app(
        tmp_path,
        '''
spec is "1.0"
ui_pack "widgets":
  version is "1.2.3"
  fragment "summary":
    text is "Hello"

page "home":
  use ui_pack "widgets" fragment "summary"
'''.lstrip(),
    )
    pack = build_ui_explain_pack(tmp_path, app_path.as_posix())
    text = render_see(pack)
    assert 'ui_pack "widgets"' in text
    assert "1.2.3" in text
    assert 'fragment "summary"' in text
