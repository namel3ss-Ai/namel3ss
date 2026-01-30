from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from namel3ss.pipelines.registry import pipeline_contracts
from namel3ss.runtime.executor import Executor
from namel3ss.runtime.memory.api import MemoryManager
from namel3ss.runtime.store.memory_store import MemoryStore
from tests.conftest import lower_ir_program

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = ROOT / "templates" / "operations" / "app.ai"
FIXTURES_DIR = ROOT / "tests" / "fixtures" / "operations"
GOLDEN_PATH = FIXTURES_DIR / "operations_explain_golden.json"

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


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def _get_job(store: MemoryStore, job_id: str) -> dict:
    jobs = store.list_records(_schema("Job"), limit=50)
    return next(job for job in jobs if job["job_id"] == job_id)


def test_operations_narrative_and_explain_goldens(tmp_path: Path) -> None:
    app_path = _stage_template(tmp_path)
    store = MemoryStore()
    state: dict = {}

    clean = _load_fixture("clean_run.json")

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="queue_job",
        input_data={
            "job_id": clean["job_id"],
            "name": clean["name"],
            "expected_outcome": clean["expected_outcome"],
        },
    )
    state = result.state
    assert result.last_value["status"] == "queued"

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="advance_job",
        input_data={"job_id": clean["job_id"], "next_state": "running", "reason": "start"},
    )
    state = result.state
    assert result.last_value["status"] == "running"

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="advance_job",
        input_data={
            "job_id": clean["job_id"],
            "next_state": "done",
            "reason": "complete",
            "actual_outcome": clean["actual_outcome"],
        },
    )
    state = result.state
    assert result.last_value["status"] == "done"

    events_before = store.list_records(_schema("ExecutionEvent"), limit=20)
    narrative = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="narrative_for_job",
        input_data={"job_id": clean["job_id"]},
    )
    events_after = store.list_records(_schema("ExecutionEvent"), limit=20)
    assert len(events_before) == len(events_after)

    summary = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="summarize_operations",
        input_data={},
    )

    payload = {
        "narrative": narrative.last_value["events"],
        "explain": store.list_records(_schema("ExplainEntry"), limit=20),
        "summary": summary.last_value,
    }
    expected = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert _normalize(payload) == expected


def test_operations_retry_and_rollback(tmp_path: Path) -> None:
    app_path = _stage_template(tmp_path)
    store = MemoryStore()
    state: dict = {}

    retry = _load_fixture("retry_job.json")

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="queue_job",
        input_data={"job_id": retry["job_id"], "name": retry["name"]},
    )
    state = result.state

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="advance_job",
        input_data={
            "job_id": retry["job_id"],
            "next_state": "blocked",
            "reason": retry["reason"],
            "failure_class": retry["failure_class"],
        },
    )
    state = result.state
    assert result.last_value["status"] == "blocked"

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="retry_job",
        input_data={"job_id": retry["job_id"], "reason": retry["reason"]},
    )
    state = result.state
    assert result.last_value["status"] == "queued"

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="advance_job",
        input_data={
            "job_id": retry["job_id"],
            "next_state": "blocked",
            "reason": retry["reason"],
            "failure_class": retry["failure_class"],
        },
    )
    state = result.state

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="retry_job",
        input_data={"job_id": retry["job_id"], "reason": retry["reason"]},
    )
    state = result.state
    assert result.last_value["status"] == "queued"

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="advance_job",
        input_data={
            "job_id": retry["job_id"],
            "next_state": "blocked",
            "reason": retry["reason"],
            "failure_class": retry["failure_class"],
        },
    )
    state = result.state

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="retry_job",
        input_data={"job_id": retry["job_id"], "reason": retry["reason"]},
    )
    state = result.state
    assert result.last_value["status"] == "retry_limit"

    job_row = _get_job(store, retry["job_id"])
    assert job_row["failure_class"] == retry["failure_class"]

    explain = store.list_records(_schema("ExplainEntry"), limit=50)
    attempts = [entry["detail"]["attempt"] for entry in explain if entry["stage"] == "retry"]
    assert attempts == [1, 2]
    assert any(entry["stage"] == "retry_denied" for entry in explain)

    rollback = _load_fixture("rollback_job.json")
    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="queue_job",
        input_data={"job_id": rollback["job_id"], "name": rollback["name"]},
    )
    state = result.state

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="advance_job",
        input_data={"job_id": rollback["job_id"], "next_state": "running", "reason": "start"},
    )
    state = result.state

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="rollback_job",
        input_data={
            "job_id": rollback["job_id"],
            "reason": rollback["reason"],
            "artifacts": rollback["artifacts"],
        },
    )
    state = result.state
    assert result.last_value["status"] == "blocked"

    job_row = _get_job(store, rollback["job_id"])
    assert job_row["rollback_status"] == "rolled_back"

    explain = store.list_records(_schema("ExplainEntry"), limit=80)
    assert any(
        entry["stage"] == "rollback" and entry["detail"]["job_id"] == rollback["job_id"]
        for entry in explain
    )


def test_operations_summary_and_ordering(tmp_path: Path) -> None:
    app_path = _stage_template(tmp_path)
    store = MemoryStore()
    state: dict = {}

    queued = _load_fixture("queued_job.json")
    running = _load_fixture("running_job.json")
    blocked = _load_fixture("blocked_job.json")
    clean = _load_fixture("clean_run.json")
    drift = _load_fixture("drift_job.json")

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="queue_job",
        input_data={"job_id": queued["job_id"], "name": queued["name"]},
    )
    state = result.state

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="queue_job",
        input_data={"job_id": running["job_id"], "name": running["name"]},
    )
    state = result.state
    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="advance_job",
        input_data={"job_id": running["job_id"], "next_state": "running", "reason": "start"},
    )
    state = result.state

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="queue_job",
        input_data={"job_id": blocked["job_id"], "name": blocked["name"]},
    )
    state = result.state
    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="advance_job",
        input_data={
            "job_id": blocked["job_id"],
            "next_state": "blocked",
            "reason": "block",
            "failure_class": blocked["failure_class"],
        },
    )
    state = result.state

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="queue_job",
        input_data={
            "job_id": clean["job_id"],
            "name": clean["name"],
            "expected_outcome": clean["expected_outcome"],
        },
    )
    state = result.state
    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="advance_job",
        input_data={
            "job_id": clean["job_id"],
            "next_state": "done",
            "reason": "complete",
            "actual_outcome": clean["actual_outcome"],
        },
    )
    state = result.state

    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="queue_job",
        input_data={
            "job_id": drift["job_id"],
            "name": drift["name"],
            "expected_outcome": drift["expected_outcome"],
        },
    )
    state = result.state
    result = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="advance_job",
        input_data={
            "job_id": drift["job_id"],
            "next_state": "done",
            "reason": "complete",
            "actual_outcome": drift["actual_outcome"],
        },
    )
    state = result.state

    summary = _run_flow(
        app_path,
        store=store,
        state=state,
        flow_name="summarize_operations",
        input_data={},
    )

    payload = summary.last_value
    jobs = payload["jobs"]
    statuses = [job["status"] for job in jobs]
    order = {"queued": 0, "running": 1, "blocked": 2, "done": 3}
    assert statuses == sorted(statuses, key=lambda value: order[value])

    health = payload["health"]
    assert health["queued"] == 1
    assert health["running"] == 1
    assert health["blocked"] == 1
    assert health["done"] == 2
    assert health["blocked_by_class"]["dependency"] == 1

    drift_summary = payload["drift"]
    assert drift_summary["status"] == "available"
    assert drift_summary["observed"] == 2
    assert drift_summary["changed"] == 1
    assert drift_summary["stable"] == 1

    cost_summary = payload["cost"]
    assert cost_summary["status"] == "not_available"
