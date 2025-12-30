from __future__ import annotations

import os
from pathlib import Path

import pytest

from namel3ss import contract as build_contract
from namel3ss.ir import nodes as ir
from namel3ss.runtime.executor.api import execute_program_flow
from namel3ss.runtime.executor.executor import Executor
from namel3ss.runtime.executor.records_ops import build_predicate_plan
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.runtime.storage.postgres_store import PostgresStore
from namel3ss.runtime.storage.sqlite_store import SQLiteStore


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
  set state.item.count is 5
  create "Item" with state.item as item
  set state.item.id is 3
  set state.item.name is "Gamma"
  set state.item.count is 1
  create "Item" with state.item as item
  return "seeded"

flow "find_over":
  find "Item" where count is greater than input.values.min
  return list length of item_results

flow "update_named":
  update "Item" where name is input.values.name set:
    count is count + input.values.bump

flow "delete_small":
  delete "Item" where count is less than input.values.max
'''


UNSUPPORTED_SOURCE = '''spec is "1.0"

record "Item":
  field "id" is number must be present
  field "meta" is json

flow "find_meta":
  find "Item" where meta.status is "active"
  return list length of item_results
'''


def _run_sequence(store, program: ir.Program) -> tuple[object, object, object, list[dict]]:
    execute_program_flow(program, "seed", store=store)
    found = execute_program_flow(
        program,
        "find_over",
        store=store,
        input={"values": {"min": 2}},
    )
    updated = execute_program_flow(
        program,
        "update_named",
        store=store,
        input={"values": {"name": "Alpha", "bump": 4}},
    )
    deleted = execute_program_flow(
        program,
        "delete_small",
        store=store,
        input={"values": {"max": 2}},
    )
    schema = next(record for record in program.records if record.name == "Item")
    items = store.list_records(schema)
    return found.last_value, updated.last_value, deleted.last_value, items


def test_sqlite_predicates_match_memory_store(tmp_path: Path) -> None:
    contract_obj = build_contract(SOURCE)
    program = contract_obj.program

    mem_store = MemoryStore()
    sql_store = SQLiteStore(tmp_path / "predicates.db")

    mem_result = _run_sequence(mem_store, program)
    sql_result = _run_sequence(sql_store, program)

    assert mem_result[:3] == sql_result[:3]
    assert mem_result[3] == sql_result[3]


def test_predicate_fallback_is_explicit(tmp_path: Path) -> None:
    contract_obj = build_contract(UNSUPPORTED_SOURCE)
    program = contract_obj.program
    flow = next(f for f in program.flows if f.name == "find_meta")
    schema = next(record for record in program.records if record.name == "Item")

    store = SQLiteStore(tmp_path / "fallback.db")
    executor = Executor(flow, schemas={schema.name: schema}, store=store)
    find_stmt = next(stmt for stmt in flow.body if isinstance(stmt, ir.Find))

    plan = build_predicate_plan(
        executor.ctx,
        schema,
        find_stmt.predicate,
        subject="Find",
        line=find_stmt.line,
        column=find_stmt.column,
    )

    assert plan.sql is None
    assert plan.sql_reason


@pytest.mark.skipif(not os.getenv("N3_TEST_DATABASE_URL"), reason="N3_TEST_DATABASE_URL not set")
def test_postgres_predicates_match_memory_store() -> None:
    pytest.importorskip("psycopg")
    contract_obj = build_contract(SOURCE)
    program = contract_obj.program

    mem_store = MemoryStore()
    pg_store = PostgresStore(os.environ["N3_TEST_DATABASE_URL"])
    pg_store.clear()
    try:
        mem_result = _run_sequence(mem_store, program)
        pg_result = _run_sequence(pg_store, program)
        assert mem_result[:3] == pg_result[:3]
        assert mem_result[3] == pg_result[3]
    finally:
        pg_store.clear()
        pg_store.close()
