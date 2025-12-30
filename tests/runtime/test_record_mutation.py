from __future__ import annotations

from namel3ss import contract as build_contract
from namel3ss.runtime.executor.api import execute_program_flow
from namel3ss.runtime.store.memory_store import MemoryStore


SOURCE = '''spec is "1.0"

record "Item":
  field "id" is number must be present
  field "name" is text must be present
  field "count" is number must be at least 0

flow "seed":
  set state.item.id is 1
  set state.item.name is "Alpha"
  set state.item.count is 2
  create "Item" with state.item as item
  set state.item.id is 2
  set state.item.name is "Beta"
  set state.item.count is 1
  create "Item" with state.item as item

flow "bump":
  update "Item" where id is 1 set:
    count is count + 3

flow "remove":
  delete "Item" where name is "Beta"
'''


def test_update_and_delete_records() -> None:
    contract_obj = build_contract(SOURCE)
    program = contract_obj.program
    store = MemoryStore()
    execute_program_flow(program, "seed", store=store)

    result = execute_program_flow(program, "bump", store=store)
    assert result.last_value == 1

    schema = next(record for record in program.records if record.name == "Item")
    items = store.list_records(schema)
    assert len(items) == 2
    alpha = next(item for item in items if item["id"] == 1)
    assert alpha["count"] == 5

    result = execute_program_flow(program, "remove", store=store)
    assert result.last_value == 1
    items = store.list_records(schema)
    assert len(items) == 1
    assert items[0]["name"] == "Alpha"
