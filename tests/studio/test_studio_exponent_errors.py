from __future__ import annotations

from pathlib import Path

from namel3ss.studio.api import execute_action, get_summary_payload
from namel3ss.studio.session import SessionState


def test_studio_exponent_parse_error_payload(tmp_path: Path):
    source = (
        'spec is "1.0"\n\n'
        'flow "demo":\n'
        "  return 2 **\n"
    )
    app_path = tmp_path / "app.ai"
    payload = get_summary_payload(source, app_path.as_posix())
    assert payload.get("ok") is False
    assert payload.get("kind") == "parse"
    location = payload.get("location") or {}
    assert location.get("line") == 4


def test_studio_exponent_runtime_type_error_payload(tmp_path: Path):
    source = (
        'spec is "1.0"\n\n'
        'flow "demo":\n'
        "  return true ** 2\n\n"
        'page "home":\n'
        '  button "Run":\n'
        '    calls flow "demo"\n'
    )
    app_path = tmp_path / "app.ai"
    app_path.write_text(source, encoding="utf-8")
    session = SessionState()
    payload = execute_action(source, session, "page.home.button.run", {}, app_path=app_path.as_posix())
    assert payload.get("ok") is False
    assert payload.get("kind") == "runtime"
    location = payload.get("location") or {}
    assert location.get("line") == 4
