from __future__ import annotations

from pathlib import Path

from namel3ss.determinism import canonical_trace_json
from namel3ss.module_loader import load_project
from namel3ss.runtime.executor import execute_program_flow
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.traces.schema import TraceEventType


FIXTURE_PATH = Path("tests/fixtures/flow_declarative_app.ai")
TRACE_GOLDEN_PATH = Path("tests/fixtures/flow_declarative_explain_golden.json")
ACTION_ID = "page.home.button.add"


def _run_flow(tmp_path: Path, input_payload: dict):
    source = FIXTURE_PATH.read_text(encoding="utf-8")
    app_file = tmp_path / "app.ai"
    app_file.write_text(source, encoding="utf-8")
    project = load_project(app_file)
    return execute_program_flow(
        project.program,
        "create_note",
        state={},
        input=input_payload,
        store=MemoryStore(),
        action_id=ACTION_ID,
    )


def _flow_traces(result) -> list[dict]:
    return [
        trace
        for trace in result.traces
        if isinstance(trace, dict)
        and trace.get("type") in {TraceEventType.FLOW_START, TraceEventType.FLOW_STEP}
    ]


def test_declarative_flow_traces_deterministic(tmp_path: Path) -> None:
    first = _run_flow(tmp_path, {"name": "Ada"})
    second = _run_flow(tmp_path, {"name": "Ada"})
    assert canonical_trace_json(_flow_traces(first)) == canonical_trace_json(_flow_traces(second))


def test_declarative_flow_trace_fields_present(tmp_path: Path) -> None:
    result = _run_flow(tmp_path, {"name": "Ada"})
    traces = _flow_traces(result)
    steps = [trace for trace in traces if trace.get("type") == TraceEventType.FLOW_STEP]
    step_ids = [step.get("step_id") for step in steps]
    assert step_ids == ["flow:create_note.input.01", "flow:create_note.create.02"]
    input_step = next(step for step in steps if step.get("step_kind") == "input")
    create_step = next(step for step in steps if step.get("step_kind") == "create")
    assert input_step.get("fields") == ["name"]
    assert create_step.get("what") == 'create "Note"'
    assert create_step.get("why") == f'action "{ACTION_ID}" ran flow "create_note"'
    assert create_step.get("changes") == {"record": "Note", "fields": ["name"]}


def test_declarative_flow_trace_golden(tmp_path: Path) -> None:
    result = _run_flow(tmp_path, {"name": "Ada"})
    actual = canonical_trace_json(_flow_traces(result))
    expected = TRACE_GOLDEN_PATH.read_text(encoding="utf-8")
    assert actual == expected
