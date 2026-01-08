from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


SOURCE = '''page "home":
  modal "Confirm":
    text is "Sure"
  drawer "Details":
    text is "More"
  card "Actions":
    actions:
      action "Open confirm":
        opens modal "Confirm"
      action "Close confirm":
        closes modal "Confirm"
      action "Open details":
        opens drawer "Details"
'''


def test_overlay_manifest_wires_actions():
    program = lower_ir_program(SOURCE)
    manifest = build_manifest(program, state={})
    page = manifest["pages"][0]
    modal = next(el for el in page["elements"] if el["type"] == "modal")
    drawer = next(el for el in page["elements"] if el["type"] == "drawer")
    card = next(el for el in page["elements"] if el["type"] == "card")

    assert modal["open"] is False
    assert drawer["open"] is False

    actions = manifest["actions"]
    assert modal.get("open_actions")
    assert modal.get("close_actions")
    for action_id in modal["open_actions"]:
        assert actions[action_id]["type"] == "open_modal"
        assert actions[action_id]["target"] == modal["id"]
    for action_id in modal["close_actions"]:
        assert actions[action_id]["type"] == "close_modal"
        assert actions[action_id]["target"] == modal["id"]
    for action_id in drawer.get("open_actions") or []:
        assert actions[action_id]["type"] == "open_drawer"
        assert actions[action_id]["target"] == drawer["id"]

    card_actions = card.get("actions") or []
    open_entry = next(action for action in card_actions if action["label"] == "Open confirm")
    close_entry = next(action for action in card_actions if action["label"] == "Close confirm")
    drawer_entry = next(action for action in card_actions if action["label"] == "Open details")
    assert open_entry["type"] == "open_modal"
    assert open_entry["target"] == modal["id"]
    assert close_entry["type"] == "close_modal"
    assert close_entry["target"] == modal["id"]
    assert drawer_entry["type"] == "open_drawer"
    assert drawer_entry["target"] == drawer["id"]
