from __future__ import annotations

import io
import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from namel3ss.ingestion.api import run_ingestion
from namel3ss.pipelines.registry import pipeline_contracts
from namel3ss.runtime.backend.upload_store import store_upload
from namel3ss.runtime.executor import Executor
from namel3ss.runtime.memory.api import MemoryManager
from namel3ss.runtime.store.memory_store import MemoryStore
from tests.conftest import lower_ir_program

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = ROOT / "templates" / "support" / "app.ai"
FIXTURES_DIR = ROOT / "tests" / "fixtures" / "support"
GOLDEN_PATH = ROOT / "tests" / "fixtures" / "support_explain_citations.json"

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
    text = (FIXTURES_DIR / filename).read_text(encoding="utf-8")
    # Normalize line endings for cross-platform checksum determinism.
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    payload = normalized.encode("utf-8")
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


def _ingest_knowledge(tmp_path: Path, state: dict, upload_id: str) -> None:
    app_path = tmp_path / "app.ai"
    run_ingestion(
        upload_id=upload_id,
        mode=None,
        state=state,
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
        secret_values=None,
    )


def _normalize(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize(val) for key, val in value.items() if key != "_id"}
    return value


def _get_case(store: MemoryStore, case_id: str) -> dict:
    cases = store.list_records(_schema("Case"), limit=20)
    return next(item for item in cases if item["case_id"] == case_id)


def test_support_knowledge_resolution_goldens(tmp_path: Path) -> None:
    app_path = _stage_template(tmp_path)
    store = MemoryStore()
    state: dict = {}

    knowledge = _store_text_upload(tmp_path, "knowledge.txt")
    _ingest_knowledge(tmp_path, state, knowledge["checksum"])

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="receive_case",
        input_data={
            "case_id": "case-knowledge",
            "title": "Reset request",
            "summary": "Reset password for account access",
            "route": "knowledge",
        },
    )
    state = result.state
    assert result.last_value["status"] == "received"

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="understand_case",
        input_data={
            "case_id": "case-knowledge",
            "query": "reset",
            "route": "knowledge",
        },
    )
    state = result.state
    assert result.last_value["status"] == "understood"

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="resolve_case",
        input_data={"case_id": "case-knowledge"},
    )
    state = result.state
    assert result.last_value["status"] == "resolved"

    case_row = _get_case(store, "case-knowledge")
    assert case_row["status"] == "resolved"

    explain = store.list_records(_schema("ExplainEntry"), limit=20)
    transitions = [entry for entry in explain if entry["stage"] == "transition"]
    assert [entry["detail"]["next"] for entry in transitions] == ["received", "understood", "resolved"]

    archive = store.list_records(_schema("CaseArchive"), limit=10)
    assert archive[0]["case_id"] == "case-knowledge"

    payload = {
        "citations": state.get("case_citations", []),
        "explain": store.list_records(_schema("ExplainEntry"), limit=20),
    }
    expected = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert _normalize(payload) == expected


def test_support_case_resolution_and_archive_remove(tmp_path: Path) -> None:
    app_path = _stage_template(tmp_path)
    store = MemoryStore()
    state: dict = {}

    knowledge = _store_text_upload(tmp_path, "knowledge.txt")
    _ingest_knowledge(tmp_path, state, knowledge["checksum"])

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="receive_case",
        input_data={
            "case_id": "case-seed",
            "title": "Billing reset",
            "summary": "Billing reset for account",
            "route": "knowledge",
        },
    )
    state = result.state

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="understand_case",
        input_data={
            "case_id": "case-seed",
            "query": "billing",
            "route": "knowledge",
        },
    )
    state = result.state

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="resolve_case",
        input_data={"case_id": "case-seed"},
    )
    state = result.state
    assert result.last_value["status"] == "resolved"

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="receive_case",
        input_data={
            "case_id": "case-followup",
            "title": "Billing followup",
            "summary": "Billing reset followup",
            "route": "cases",
        },
    )
    state = result.state

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="understand_case",
        input_data={
            "case_id": "case-followup",
            "query": "billing",
            "route": "cases",
        },
    )
    state = result.state

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="resolve_case",
        input_data={"case_id": "case-followup"},
    )
    state = result.state
    assert result.last_value["status"] == "resolved"

    citations = state.get("case_citations", [])
    assert citations[0]["source_type"] == "case"

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="receive_case",
        input_data={
            "case_id": "case-seed",
            "title": "Billing reset",
            "summary": "Billing reset updated",
            "route": "knowledge",
        },
    )
    state = result.state

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="understand_case",
        input_data={
            "case_id": "case-seed",
            "query": "billing",
            "route": "knowledge",
        },
    )
    state = result.state

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="resolve_case",
        input_data={"case_id": "case-seed"},
    )
    state = result.state

    case_index = state.get("case_index", {}).get("chunks", [])
    case_seed_chunks = [chunk for chunk in case_index if chunk.get("upload_id") == "case-seed"]
    assert len(case_seed_chunks) == 1

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="remove_case_archive",
        input_data={"case_id": "case-seed"},
    )
    state = result.state
    assert result.last_value["status"] == "removed"

    case_index = state.get("case_index", {}).get("chunks", [])
    assert not any(chunk.get("upload_id") == "case-seed" for chunk in case_index)

    explain = store.list_records(_schema("ExplainEntry"), limit=50)
    assert any(entry.get("stage") == "archive_remove" for entry in explain)


def test_support_escalations(tmp_path: Path) -> None:
    app_path = _stage_template(tmp_path)
    store = MemoryStore()
    state: dict = {}

    knowledge = _store_text_upload(tmp_path, "knowledge.txt")
    _ingest_knowledge(tmp_path, state, knowledge["checksum"])

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="receive_case",
        input_data={
            "case_id": "case-unknown",
            "title": "Unknown issue",
            "summary": "Unmatched issue",
            "route": "knowledge",
        },
    )
    state = result.state

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="understand_case",
        input_data={
            "case_id": "case-unknown",
            "query": "nonexistent",
            "route": "knowledge",
        },
    )
    state = result.state

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="resolve_case",
        input_data={"case_id": "case-unknown"},
    )
    state = result.state
    assert result.last_value["status"] == "escalated"

    explain = store.list_records(_schema("ExplainEntry"), limit=20)
    escalation = next(
        entry
        for entry in explain
        if entry["stage"] == "transition" and entry["detail"]["next"] == "escalated"
    )
    assert escalation["detail"]["reason"] == "no_sources"

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="receive_case",
        input_data={
            "case_id": "case-policy",
            "title": "Policy issue",
            "summary": "Reset with policy restriction",
            "route": "knowledge",
            "policy_code": "restricted",
        },
    )
    state = result.state

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="understand_case",
        input_data={
            "case_id": "case-policy",
            "query": "reset",
            "route": "knowledge",
        },
    )
    state = result.state

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="resolve_case",
        input_data={"case_id": "case-policy"},
    )
    state = result.state
    assert result.last_value["status"] == "escalated"

    explain = store.list_records(_schema("ExplainEntry"), limit=50)
    policy_escalation = next(
        entry
        for entry in explain
        if entry["stage"] == "transition"
        and entry["detail"]["case_id"] == "case-policy"
        and entry["detail"]["next"] == "escalated"
    )
    assert policy_escalation["detail"]["reason"] == "policy"

