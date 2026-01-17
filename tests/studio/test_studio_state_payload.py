from __future__ import annotations

from namel3ss.studio import api
from namel3ss.studio.session import SessionState
from namel3ss.studio.state_api import get_state_payload


SOURCE = '''spec is "1.0"

record "Item":
  field "id" is number must be present
  field "name" is text must be present

flow "seed":
  set state.item.id is 10
  set state.item.name is "Ten"
  create "Item" with state.item as item
  set state.item.id is 2
  set state.item.name is "Two"
  create "Item" with state.item as item

page "home":
  button "Seed":
    calls flow "seed"
'''


def test_studio_state_payload_includes_records_and_effects(tmp_path):
    app_path = tmp_path / "app.ai"
    app_path.write_text(SOURCE, encoding="utf-8")
    session = SessionState()
    actions = api.get_actions_payload(SOURCE, app_path.as_posix())
    action_id = actions["actions"][0]["id"]

    api.execute_action(SOURCE, session, action_id, {}, app_path.as_posix())
    payload = get_state_payload(SOURCE, session, app_path.as_posix())

    assert payload["ok"] is True
    records = payload.get("records") or []
    assert records and records[0]["name"] == "Item"
    assert records[0]["fields"] == [{"name": "id", "type": "number"}, {"name": "name", "type": "text"}]
    rows = records[0]["rows"]
    assert [row["id"] for row in rows] == [2, 10]

    effects = payload.get("effects") or {}
    assert effects.get("action", {}).get("id") == action_id
    changes = effects.get("records") or []
    assert changes and changes[0]["ids"] == [2, 10]
