import json

from namel3ss.runtime.audit.recorder import audit_schema
from namel3ss.runtime.executor import Executor
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse


SOURCE = '''spec is "1.0"

record "Item":
  field "name" is text

flow "seed": audited requires true
  save Item
'''


def test_audit_entry_includes_record_ids_and_proof(tmp_path):
    app_path = tmp_path / "app.ai"
    app_path.write_text(SOURCE, encoding="utf-8")
    (tmp_path / ".namel3ss").mkdir()
    active_proof = {"proof_id": "proof-123", "build_id": "local-abc", "target": "local"}
    (tmp_path / ".namel3ss" / "active_proof.json").write_text(json.dumps(active_proof), encoding="utf-8")
    program = lower_program(parse(SOURCE))
    flow = program.flows[0]
    schemas = {schema.name: schema for schema in program.records}
    store = MemoryStore()
    executor = Executor(
        flow,
        schemas=schemas,
        initial_state={"item": {"name": "Widget"}},
        store=store,
        project_root=str(tmp_path),
    )
    executor.run()
    records = store.list_records(audit_schema())
    assert records
    entry = records[0]
    assert entry["record_ids"]
    assert entry["proof_id"] == "proof-123"
    assert entry["build_id"] == "local-abc"
