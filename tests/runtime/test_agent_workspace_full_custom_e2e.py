from __future__ import annotations

from pathlib import Path

from tests.conftest import run_flow


SOURCE = Path("tests/fixtures/agent_workspace/full_custom.ai").read_text(encoding="utf-8")


def test_full_custom_agent_answer_falls_back_for_empty_context() -> None:
    result = run_flow(
        SOURCE,
        flow_name="agent.answer",
        input_data={
            "message": "What is in the workspace?",
            "context": "",
        },
    )
    payload = result.last_value
    assert isinstance(payload, dict)
    assert payload["answer_text"] == "No grounded support found in indexed sources for this query."
    assert payload["citations"] == []


def test_full_custom_agent_answer_runs_multi_step_orchestration() -> None:
    result = run_flow(
        SOURCE,
        flow_name="agent.answer",
        input_data={
            "message": "What is in the workspace?",
            "context": "Workspace context for deterministic full-custom example.",
        },
    )
    payload = result.last_value
    assert isinstance(payload, dict)
    assert isinstance(payload.get("answer_text"), str)
    assert payload["answer_text"] != ""

    traces = [trace for trace in result.traces if isinstance(trace, dict)]
    started = [trace for trace in traces if trace.get("type") == "flow_call_started"]

    assert any(trace.get("callee_flow") == "agent.route" for trace in started)
    assert any(trace.get("callee_flow") == "agent.plan" for trace in started)
    assert any(trace.get("callee_flow") == "agent.retrieve" for trace in started)


def test_full_custom_agent_trace_sequence_is_deterministic_for_same_input() -> None:
    input_data = {
        "message": "What is in the workspace?",
        "context": "Workspace context for deterministic full-custom example.",
    }
    first = run_flow(SOURCE, flow_name="agent.answer", input_data=input_data)
    second = run_flow(SOURCE, flow_name="agent.answer", input_data=input_data)

    def _sequence(result) -> list[tuple[object, object, object]]:
        traces = [trace for trace in result.traces if isinstance(trace, dict)]
        return [
            (trace.get("type"), trace.get("callee_flow"), trace.get("status"))
            for trace in traces
        ]

    assert _sequence(first) == _sequence(second)
