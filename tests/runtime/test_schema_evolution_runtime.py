from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.executor import Executor
from namel3ss.runtime.storage.sqlite_store import SQLiteStore
from namel3ss.schema.evolution import write_workspace_snapshot
from tests.conftest import lower_ir_program


SOURCE_V1 = '''spec is "1.0"

record "Note":
  title text

flow "demo":
  return "ok"
'''

SOURCE_V2 = '''spec is "1.0"

record "Note":
  title number

flow "demo":
  return "ok"
'''


def test_runtime_blocks_incompatible_schema(tmp_path) -> None:
    program_before = lower_ir_program(SOURCE_V1)
    store = SQLiteStore(tmp_path / ".namel3ss" / "data.db")
    write_workspace_snapshot(program_before.records, project_root=tmp_path, store=store)

    program_after = lower_ir_program(SOURCE_V2)
    flow = next(flow for flow in program_after.flows if flow.name == "demo")
    schemas = {schema.name: schema for schema in program_after.records}

    with pytest.raises(Namel3ssError) as exc:
        Executor(flow, schemas=schemas, store=store, project_root=str(tmp_path)).run()

    details = exc.value.details or {}
    assert details.get("code") == "schema.incompatible"
    store.close()
