from __future__ import annotations

from tests.conftest import run_flow


SOURCE = '''spec is "1.0"
use preset "agent_workspace":
  title is "Agent Workspace"
  model is "gpt-4o-mini"
'''

CONTROLLED_OVERRIDE_SOURCE = '''spec is "1.0"
use preset "agent_workspace":
  title is "Agent Workspace"
  model is "gpt-4o-mini"

override flow "agent.route":
  return map:
    "route" is "single_agent"
    "query" is "custom: " + input.message
    "context" is input.context

override flow "agent.fallback":
  return map:
    "answer_text" is "OVERRIDE FALLBACK: " + input.message
    "citations" is list:
'''


def test_agent_workspace_answer_returns_no_support_for_empty_context() -> None:
    result = run_flow(
        SOURCE,
        flow_name="agent.answer",
        input_data={
            "message": "What does this project do?",
        },
    )
    payload = result.last_value
    assert isinstance(payload, dict)
    assert payload["answer_text"] == "No grounded support found in indexed sources for this query."
    assert payload["citations"] == []


def test_agent_workspace_answer_traces_prompt_route_and_retrieval_calls() -> None:
    result = run_flow(
        SOURCE,
        flow_name="agent.answer",
        input_data={
            "message": "Summarize this workspace.",
            "context": "Grounded context from indexed sources.",
        },
    )
    payload = result.last_value
    assert isinstance(payload, dict)
    assert isinstance(payload.get("answer_text"), str)
    assert payload["answer_text"] != ""

    traces = [trace for trace in result.traces if isinstance(trace, dict)]
    started_calls = [trace for trace in traces if trace.get("type") == "flow_call_started"]
    finished_calls = [trace for trace in traces if trace.get("type") == "flow_call_finished"]

    route_started = next(
        trace for trace in started_calls if trace.get("callee_flow") == "agent.route"
    )
    assert route_started.get("caller_flow") == "agent.answer"
    assert route_started.get("inputs") == ["message", "context"]

    assert any(
        trace.get("callee_flow") == "agent.route" and trace.get("status") == "ok"
        for trace in finished_calls
    )
    assert any(trace.get("callee_flow") == "agent.retrieve" for trace in started_calls)


def test_agent_workspace_controlled_overrides_apply_without_copying_preset_internals() -> None:
    route_result = run_flow(
        CONTROLLED_OVERRIDE_SOURCE,
        flow_name="agent.route",
        input_data={
            "message": "Where is the data?",
            "context": "deterministic context",
        },
    )
    route_payload = route_result.last_value
    assert isinstance(route_payload, dict)
    assert route_payload["query"] == "custom: Where is the data?"

    answer_result = run_flow(
        CONTROLLED_OVERRIDE_SOURCE,
        flow_name="agent.answer",
        input_data={
            "message": "Where is the data?",
            "context": "",
        },
    )
    answer_payload = answer_result.last_value
    assert isinstance(answer_payload, dict)
    assert answer_payload["answer_text"] == "OVERRIDE FALLBACK: Where is the data?"

    traces = [trace for trace in answer_result.traces if isinstance(trace, dict)]
    started_calls = [trace for trace in traces if trace.get("type") == "flow_call_started"]
    assert any(trace.get("callee_flow") == "agent.route" for trace in started_calls)
    assert any(trace.get("callee_flow") == "agent.fallback" for trace in started_calls)
