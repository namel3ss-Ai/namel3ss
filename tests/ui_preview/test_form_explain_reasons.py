from pathlib import Path

from namel3ss.runtime.ui.explain.builder import build_ui_explain_pack
from namel3ss.runtime.ui.explain.render_plain import render_see


def _write_app(tmp_path: Path, content: str) -> Path:
    app_path = tmp_path / "app.ai"
    app_path.write_text(content, encoding="utf-8")
    return app_path


def test_form_groups_and_help_are_in_see_output(tmp_path: Path) -> None:
    app_path = _write_app(
        tmp_path,
        '''
spec is "1.0"
record "User":
  name text must be present
  email text

page "home":
  form is "User":
    groups:
      group "Main":
        field name
    fields:
      field name:
        help is "Your name"
        readonly is true
'''.lstrip(),
    )
    pack = build_ui_explain_pack(tmp_path, app_path.as_posix())
    text = render_see(pack)
    assert "groups:" in text
    assert "help:" in text
    assert "readonly:" in text
