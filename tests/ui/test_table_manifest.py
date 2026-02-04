import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


CONFIG_SOURCE = '''record "Order":
  name text
  score number
  status text

flow "open_order":
  return "ok"

page "home":
  table is "Order":
    columns:
      include name
      include score
      label score is "Score"
      exclude status
    empty_text is "No orders yet."
    sort:
      by is score
      order is asc
    pagination:
      page_size is 2
    selection is multi
    row_actions:
      row_action "Open":
        calls flow "open_order"
'''


SORT_SOURCE = '''record "Order":
  name text
  score number

page "home":
  table is "Order":
    sort:
      by is score
      order is asc
'''

STATE_SOURCE = '''page "home":
  table from state results:
    columns:
      include name
      include score
      label score is "Score"
'''

def _load_record(program, name: str):
    return next(record for record in program.records if record.name == name)


def test_table_manifest_config_and_actions():
    program = lower_ir_program(CONFIG_SOURCE)
    store = MemoryStore()
    record = _load_record(program, "Order")
    store.save(record, {"name": "Alpha", "score": 10, "status": "new"})
    store.save(record, {"name": "Beta", "score": 10, "status": "new"})
    store.save(record, {"name": "Gamma", "score": 5, "status": "old"})
    manifest = build_manifest(program, state={}, store=store)
    assert manifest == build_manifest(program, state={}, store=store)
    table = next(el for el in manifest["pages"][0]["elements"] if el["type"] == "table")

    assert [col["name"] for col in table["columns"]] == ["name", "score"]
    assert table["columns"][1]["label"] == "Score"
    assert table["empty_text"] == "No orders yet."
    assert table["sort"] == {"by": "score", "order": "asc"}
    assert table["pagination"] == {"page_size": 2}
    assert table["selection"] == "multi"
    assert table["id_field"] == "_id"
    assert len(table["rows"]) == 2
    assert [row["name"] for row in table["rows"]] == ["Gamma", "Alpha"]

    actions = manifest["actions"]
    row_actions = table.get("row_actions") or []
    assert len(row_actions) == 1
    action_id = row_actions[0]["id"]
    assert action_id in actions
    assert actions[action_id]["type"] == "call_flow"
    assert actions[action_id]["flow"] == "open_order"
    assert all(table["id_field"] in row for row in table["rows"])


def test_table_sort_is_stable_for_ties():
    program = lower_ir_program(SORT_SOURCE)
    store = MemoryStore()
    record = _load_record(program, "Order")
    store.save(record, {"name": "Alpha", "score": 10})
    store.save(record, {"name": "Beta", "score": 10})
    store.save(record, {"name": "Gamma", "score": 5})
    manifest = build_manifest(program, state={}, store=store)
    table = next(el for el in manifest["pages"][0]["elements"] if el["type"] == "table")
    assert [row["name"] for row in table["rows"]] == ["Gamma", "Alpha", "Beta"]


def test_table_sort_missing_value_errors():
    program = lower_ir_program(SORT_SOURCE)
    store = MemoryStore()
    record = _load_record(program, "Order")
    store.save(record, {"name": "Alpha", "score": 10})
    store.save(record, {"name": "Missing"})
    with pytest.raises(Namel3ssError) as exc:
        build_manifest(program, state={}, store=store)
    assert "missing" in str(exc.value).lower()


def test_state_table_manifest_preserves_order():
    program = lower_ir_program(STATE_SOURCE)
    state = {
        "results": [
            {"name": "First", "score": 10},
            {"name": "Second", "score": 5},
        ]
    }
    manifest = build_manifest(program, state=state, store=MemoryStore())
    table = next(el for el in manifest["pages"][0]["elements"] if el["type"] == "table")
    assert table["source"] == "state.results"
    assert [col["name"] for col in table["columns"]] == ["name", "score"]
    assert table["columns"][1]["label"] == "Score"
    assert table.get("record") is None
    assert [row["name"] for row in table["rows"]] == ["First", "Second"]
    assert table.get("row_actions") is None


def test_state_table_requires_list_source():
    program = lower_ir_program(STATE_SOURCE)
    with pytest.raises(Namel3ssError) as exc:
        build_manifest(program, state={"results": {"name": "Bad"}}, store=MemoryStore())
    assert "table source must be a list" in str(exc.value).lower()
