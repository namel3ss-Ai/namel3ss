from pathlib import Path

from namel3ss.runtime.ui.explain.builder import build_ui_explain_pack
from namel3ss.runtime.ui.explain.render_plain import render_see


def _write_app(tmp_path: Path, content: str) -> Path:
    app_path = tmp_path / "app.ai"
    app_path.write_text(content, encoding="utf-8")
    return app_path


def _write_config(tmp_path: Path, content: str) -> None:
    config_path = tmp_path / "namel3ss.toml"
    config_path.write_text(content, encoding="utf-8")


def test_actions_blocked_reason_is_printed(tmp_path: Path) -> None:
    app_path = _write_app(
        tmp_path,
        """
page "home":
  button "Delete":
    calls flow "delete"

flow "delete": requires identity.role is "admin"
  return "ok"
""".lstrip(),
    )
    _write_config(
        tmp_path,
        """
[identity]
role = "guest"
""".lstrip(),
    )
    pack = build_ui_explain_pack(tmp_path, app_path.as_posix())
    text = render_see(pack)
    assert "not available" in text
    assert "identity.role" in text
