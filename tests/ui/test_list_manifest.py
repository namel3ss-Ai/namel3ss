import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


DEFAULT_SOURCE = '''record "Order":
  name text must be present
  status text

page "home":
  list is "Order"
'''


ACTION_SOURCE = '''record "Order":
  name text
  status text

flow "open_order":
  return "ok"

page "home":
  list is "Order":
    variant is single_line
    item:
      primary is name
    empty_text is "No orders yet."
    selection is multi
    actions:
      action "Open":
        calls flow "open_order"
'''

ACTION_WITH_INTERACTION_SOURCE = '''record "Order":
  name text

flow "rename_order":
  return "ok"

page "home":
  list is "Order":
    item:
      primary is name
    actions:
      action "Rename":
        calls flow "rename_order"
        interaction is rename_modal
'''


ID_FALLBACK_SOURCE = '''record "Metric":
  value number

page "home":
  list is "Metric"
'''

STATE_SOURCE = '''page "home":
  list from state items:
    item:
      primary is name
      secondary is detail
'''

ICON_PLAIN_SOURCE = '''record "Project":
  name text
  icon text

flow "open_project":
  return "ok"

page "home":
  list is "Project":
    variant is icon_plain
    item:
      primary is name
      icon is icon
    actions:
      action "Open":
        calls flow "open_project"
'''

def _load_record(program, name: str):
    return next(record for record in program.records if record.name == name)


def test_list_manifest_defaults_are_deterministic():
    program = lower_ir_program(DEFAULT_SOURCE)
    store = MemoryStore()
    record = _load_record(program, "Order")
    store.save(record, {"name": "Alpha", "status": "new"})
    store.save(record, {"name": "Beta", "status": "old"})
    manifest = build_manifest(program, state={}, store=store)
    assert manifest == build_manifest(program, state={}, store=store)
    list_el = next(el for el in manifest["pages"][0]["elements"] if el["type"] == "list")
    assert list_el["variant"] == "two_line"
    assert list_el["item"]["primary"] == "name"
    assert list_el.get("selection") is None


def test_list_manifest_actions_and_selection():
    program = lower_ir_program(ACTION_SOURCE)
    store = MemoryStore()
    record = _load_record(program, "Order")
    store.save(record, {"name": "Alpha", "status": "new"})
    store.save(record, {"name": "Beta", "status": "old"})
    manifest = build_manifest(program, state={}, store=store)
    list_el = next(el for el in manifest["pages"][0]["elements"] if el["type"] == "list")
    assert list_el["variant"] == "single_line"
    assert list_el["empty_text"] == "No orders yet."
    assert list_el["selection"] == "multi"
    assert list_el["id_field"] == "_id"
    actions = list_el.get("actions") or []
    assert len(actions) == 1
    action_id = actions[0]["id"]
    assert action_id in manifest["actions"]
    assert manifest["actions"][action_id]["type"] == "call_flow"
    assert manifest["actions"][action_id]["flow"] == "open_order"
    assert all(list_el["id_field"] in row for row in list_el["rows"])


def test_list_default_primary_falls_back_to_id():
    program = lower_ir_program(ID_FALLBACK_SOURCE)
    manifest = build_manifest(program, state={}, store=MemoryStore())
    list_el = next(el for el in manifest["pages"][0]["elements"] if el["type"] == "list")
    assert list_el["item"]["primary"] == "_id"


def test_list_manifest_empty_state_always_present():
    """Empty collections get a deterministic empty_state so the UI can render an empty state."""
    program = lower_ir_program(DEFAULT_SOURCE)
    manifest = build_manifest(program, state={}, store=MemoryStore())
    list_el = next(el for el in manifest["pages"][0]["elements"] if el["type"] == "list")
    assert "empty_state" in list_el
    assert list_el["empty_state"]["title"] == "No items"
    assert list_el["empty_state"]["text"] == "There are no items to display."
    assert len(list_el["rows"]) == 0
    # Manifest remains stable across runs
    assert manifest == build_manifest(program, state={}, store=MemoryStore())


def test_list_manifest_empty_state_uses_app_empty_text_when_set():
    """When the app sets empty_text, empty_state.text uses it."""
    program = lower_ir_program(ACTION_SOURCE)
    manifest = build_manifest(program, state={}, store=MemoryStore())
    list_el = next(el for el in manifest["pages"][0]["elements"] if el["type"] == "list")
    assert list_el["empty_state"]["title"] == "No items"
    assert list_el["empty_state"]["text"] == "No orders yet."
    assert list_el["empty_text"] == "No orders yet."
def test_state_list_manifest_preserves_order():
    program = lower_ir_program(STATE_SOURCE)
    state = {
        "items": [
            {"name": "First", "detail": "One"},
            {"name": "Second", "detail": "Two"},
        ]
    }
    manifest = build_manifest(program, state=state, store=MemoryStore())
    list_el = next(el for el in manifest["pages"][0]["elements"] if el["type"] == "list")
    assert list_el["source"] == "state.items"
    assert list_el.get("record") is None
    assert list_el["item"]["primary"] == "name"
    assert list_el["item"]["secondary"] == "detail"
    assert [row["name"] for row in list_el["rows"]] == ["First", "Second"]


def test_state_list_requires_list_source():
    program = lower_ir_program(STATE_SOURCE)
    with pytest.raises(Namel3ssError) as exc:
        build_manifest(program, state={"items": "bad"}, store=MemoryStore())
    assert "list source must be a list" in str(exc.value).lower()


def test_list_manifest_icon_plain_variant():
    program = lower_ir_program(ICON_PLAIN_SOURCE)
    store = MemoryStore()
    record = _load_record(program, "Project")
    store.save(record, {"name": "namel3ss", "icon": "folder_info"})
    manifest = build_manifest(program, state={}, store=store)
    list_el = next(el for el in manifest["pages"][0]["elements"] if el["type"] == "list")
    assert list_el["variant"] == "icon_plain"
    assert list_el["item"]["icon"] == "icon"
    assert len(list_el.get("actions") or []) == 1


def test_list_manifest_action_interaction_hint_is_exported():
    program = lower_ir_program(ACTION_WITH_INTERACTION_SOURCE)
    store = MemoryStore()
    record = _load_record(program, "Order")
    store.save(record, {"name": "Alpha"})
    manifest = build_manifest(program, state={}, store=store)
    list_el = next(el for el in manifest["pages"][0]["elements"] if el["type"] == "list")
    actions = list_el.get("actions") or []
    assert len(actions) == 1
    assert actions[0]["ui_behavior"] == "rename_modal"
    action_id = actions[0]["id"]
    assert manifest["actions"][action_id]["ui_behavior"] == "rename_modal"
