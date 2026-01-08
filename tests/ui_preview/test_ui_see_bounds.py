from pathlib import Path

from namel3ss.runtime.ui.explain.builder import build_ui_explain_pack
from namel3ss.runtime.ui.explain.render_plain import render_see


def _write_app(tmp_path: Path, content: str) -> Path:
    app_path = tmp_path / "app.ai"
    app_path.write_text(content, encoding="utf-8")
    return app_path


def test_see_output_truncates_long_lists(tmp_path: Path) -> None:
    fields = "\n".join([f'  f{i} text' for i in range(1, 13)])
    columns = "\n".join([f"      include f{i}" for i in range(1, 13)])
    source = f'''spec is "1.0"
record "Item":
{fields}

page "home":
  table is "Item":
    columns:
{columns}
'''
    app_path = _write_app(tmp_path, source)
    pack = build_ui_explain_pack(tmp_path, app_path.as_posix())
    text = render_see(pack)
    assert "columns:" in text
    assert "... (+4 more)" in text
