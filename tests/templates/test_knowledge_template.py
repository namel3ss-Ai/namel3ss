from __future__ import annotations

import io
import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from namel3ss.pipelines.registry import pipeline_contracts
from namel3ss.runtime.backend.upload_store import store_upload
from namel3ss.runtime.executor import Executor
from namel3ss.runtime.memory.api import MemoryManager
from namel3ss.runtime.store.memory_store import MemoryStore
from tests.conftest import lower_ir_program

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = ROOT / "templates" / "knowledge" / "app.ai"
FIXTURES_DIR = ROOT / "tests" / "fixtures" / "knowledge"
GOLDEN_PATH = ROOT / "tests" / "fixtures" / "knowledge_explain_citations.json"

TEMPLATE_SOURCE = TEMPLATE_PATH.read_text(encoding="utf-8")
PROGRAM = lower_ir_program(TEMPLATE_SOURCE)
SCHEMAS = {schema.name: schema for schema in PROGRAM.records}
FLOWS = {flow.name: flow for flow in PROGRAM.flows}


class _NoopMemoryManager(MemoryManager):
    def persist(self, *args, **kwargs) -> None:
        return None


def _stage_template(tmp_path: Path) -> Path:
    app_path = tmp_path / "app.ai"
    app_path.write_text(TEMPLATE_SOURCE, encoding="utf-8")
    return app_path


def _store_text_upload(tmp_path: Path, filename: str) -> dict:
    payload = (FIXTURES_DIR / filename).read_bytes()
    app_path = tmp_path / "app.ai"
    ctx = SimpleNamespace(project_root=str(tmp_path), app_path=app_path.as_posix())
    return store_upload(ctx, filename=filename, content_type="text/plain", stream=io.BytesIO(payload))


def _run_flow(app_path: Path, *, store: MemoryStore, state: dict, flow_name: str, input_data: dict):
    flow = FLOWS.get(flow_name)
    if flow is None:
        raise ValueError(f"Flow '{flow_name}' not found")
    executor = Executor(
        flow,
        schemas=SCHEMAS,
        initial_state=state,
        store=store,
        input_data=input_data,
        functions=PROGRAM.functions,
        flows=FLOWS,
        flow_contracts=getattr(PROGRAM, "flow_contracts", {}) or {},
        pipeline_contracts=pipeline_contracts(),
        capabilities=getattr(PROGRAM, "capabilities", ()),
        identity_schema=getattr(PROGRAM, "identity", None),
        pack_allowlist=getattr(PROGRAM, "pack_allowlist", None),
        policy=getattr(PROGRAM, "policy", None),
        project_root=str(app_path.parent),
        app_path=app_path.as_posix(),
        memory_manager=_NoopMemoryManager(),
    )
    return executor.run()


def _schema(name: str):
    return SCHEMAS[name]


def _normalize(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize(val) for key, val in value.items() if key != "_id"}
    return value


def test_knowledge_ingest_new_and_reject(tmp_path: Path) -> None:
    app_path = _stage_template(tmp_path)
    store = MemoryStore()
    state: dict = {}

    valid = _store_text_upload(tmp_path, "valid.txt")
    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="ingest_document",
        input_data={
            "upload_id": valid["checksum"],
            "document_id": "policy",
            "title": "Policy Guide",
        },
    )
    state = result.state
    assert result.last_value["status"] == "new"
    assert state["ingestion"][valid["checksum"]]["status"] == "pass"
    assert any(entry.get("upload_id") == valid["checksum"] for entry in state["index"]["chunks"])

    rejected = _store_text_upload(tmp_path, "rejected.txt")
    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="ingest_document",
        input_data={
            "upload_id": rejected["checksum"],
            "document_id": "rejected",
            "title": "Rejected",
        },
    )
    state = result.state
    assert result.last_value["status"] == "reject"
    assert state["ingestion"][rejected["checksum"]]["status"] == "block"
    assert not any(entry.get("upload_id") == rejected["checksum"] for entry in state["index"]["chunks"])

    docs = store.list_records(_schema("Document"), limit=10)
    doc_map = {doc["document_id"]: doc for doc in docs}
    assert doc_map["policy"]["status"] == "active"
    assert doc_map["rejected"]["status"] == "rejected"

    changes = store.list_records(_schema("DocumentChange"), limit=10)
    assert [change["event"] for change in changes] == ["new", "reject"]


def test_knowledge_update_and_remove(tmp_path: Path) -> None:
    app_path = _stage_template(tmp_path)
    store = MemoryStore()
    state: dict = {}

    base = _store_text_upload(tmp_path, "update_base.txt")
    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="ingest_document",
        input_data={
            "upload_id": base["checksum"],
            "document_id": "ops",
            "title": "Operations Policy",
        },
    )
    state = result.state

    revised = _store_text_upload(tmp_path, "update_revised.txt")
    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="ingest_document",
        input_data={
            "upload_id": revised["checksum"],
            "document_id": "ops",
            "title": "Operations Policy",
        },
    )
    state = result.state
    assert result.last_value["status"] == "update"

    chunks = state.get("index", {}).get("chunks", [])
    assert not any(entry.get("upload_id") == base["checksum"] for entry in chunks)
    assert any(entry.get("upload_id") == revised["checksum"] for entry in chunks)

    docs = store.list_records(_schema("Document"), limit=10)
    doc = next(item for item in docs if item["document_id"] == "ops")
    assert doc["upload_id"] == revised["checksum"]
    assert doc["status"] == "active"

    changes = store.list_records(_schema("DocumentChange"), limit=10)
    assert changes[-1]["event"] == "update"
    assert changes[-1]["previous_upload_id"] == base["checksum"]

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="remove_document",
        input_data={"document_id": "ops"},
    )
    state = result.state
    assert result.last_value["status"] == "removed"

    docs = store.list_records(_schema("Document"), limit=10)
    doc = next(item for item in docs if item["document_id"] == "ops")
    assert doc["status"] == "removed"

    chunks = state.get("index", {}).get("chunks", [])
    assert not any(entry.get("upload_id") == revised["checksum"] for entry in chunks)

    changes = store.list_records(_schema("DocumentChange"), limit=10)
    assert changes[-1]["event"] == "remove"
    assert changes[-1]["status"] == "removed"


def test_knowledge_citations_and_explain_goldens(tmp_path: Path) -> None:
    app_path = _stage_template(tmp_path)
    store = MemoryStore()
    state: dict = {}

    valid = _store_text_upload(tmp_path, "valid.txt")
    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="ingest_document",
        input_data={
            "upload_id": valid["checksum"],
            "document_id": "policy",
            "title": "Policy Guide",
        },
    )
    state = result.state

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="answer_query",
        input_data={"query": "Policy"},
    )
    state = result.state

    explain = store.list_records(_schema("ExplainEntry"), limit=10)
    payload = {
        "citations": state.get("chat", {}).get("citations", []),
        "explain": explain,
    }
    expected = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert _normalize(payload) == expected
