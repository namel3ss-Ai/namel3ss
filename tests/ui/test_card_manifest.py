from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


SOURCE = '''flow "go":
  return "ok"

page "home":
  card_group:
    card "Summary":
      stat:
        value is state.total
        label is "Total"
      actions:
        action "Run":
          calls flow "go"
      text is "Done"
'''


def test_card_group_manifest_includes_actions_and_stat():
    program = lower_ir_program(SOURCE)
    manifest = build_manifest(program, state={"total": 42})
    page = manifest["pages"][0]
    group = page["elements"][0]
    assert group["type"] == "card_group"
    card = group["children"][0]
    assert card["type"] == "card"
    assert card["stat"]["value"] == 42
    assert card["stat"]["label"] == "Total"
    assert card["stat"]["source"] == "state.total"
    action_entry = card["actions"][0]
    action_id = action_entry["id"]
    assert action_entry["label"] == "Run"
    assert action_id == "page.home.card.0.0.action.run"
    assert action_id in manifest["actions"]
    assert manifest["actions"][action_id]["type"] == "call_flow"
    assert manifest["actions"][action_id]["flow"] == "go"
