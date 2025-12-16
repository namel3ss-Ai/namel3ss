from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.studio.api import execute_action, get_ui_payload
from namel3ss.studio.session import SessionState


APP_SOURCE = '''
record "User":
  name string must be present

flow "demo":
  let result is "hi"
  return result

page "home":
  button "Run":
    calls flow "demo"
  form is "User"
  table is "User"
'''.lstrip()


def test_action_flow_and_form_execution(tmp_path: Path) -> None:
    app_file = tmp_path / "app.ai"
    app_file.write_text(APP_SOURCE, encoding="utf-8")
    session = SessionState()

    call_resp = execute_action(APP_SOURCE, session, "page.home.button.run", {})
    assert call_resp["ok"] is True
    assert call_resp["result"] == "hi"
    assert isinstance(call_resp["state"], dict)

    with pytest.raises(Namel3ssError):
        execute_action(APP_SOURCE, session, "page.home.form.user", {})

    good_form = execute_action(APP_SOURCE, session, "page.home.form.user", {"values": {"name": "Alice"}})
    assert good_form["ok"] is True
    assert session.state.get("user", {}).get("name") == "Alice"

    manifest = get_ui_payload(APP_SOURCE, session)
    tables = [el for p in manifest.get("pages", []) for el in p.get("elements", []) if el.get("type") == "table"]
    assert tables
    assert any(row.get("name") == "Alice" for row in tables[0].get("rows", []))
