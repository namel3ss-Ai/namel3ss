from namel3ss.traces.builders import build_agent_step_end, build_agent_step_start
from namel3ss.traces.schema import TRACE_VERSION, TraceEventType


def test_agent_step_start_trace_event() -> None:
    event = build_agent_step_start(
        agent_name="planner",
        agent_id="planner",
        role="Plans",
        step_id="step:0001",
        reason="invoked by flow demo",
    )
    assert event["type"] == TraceEventType.AGENT_STEP_START
    assert event["trace_version"] == TRACE_VERSION
    assert event["agent_name"] == "planner"
    assert event["agent_id"] == "planner"
    assert event["role"] == "Plans"
    assert event["step_id"] == "step:0001"
    assert event["lines"] == ["invoked by flow demo"]


def test_agent_step_end_trace_event_includes_memory_facts() -> None:
    memory_facts = {"keys": ["fact"], "counts": {"total": 1}, "last_updated_step": "step:0001"}
    event = build_agent_step_end(
        agent_name="planner",
        agent_id="planner",
        role=None,
        step_id="step:0002",
        reason="invoked by flow demo",
        status="ok",
        memory_facts=memory_facts,
    )
    assert event["type"] == TraceEventType.AGENT_STEP_END
    assert event["trace_version"] == TRACE_VERSION
    assert event["status"] == "ok"
    assert event["memory_facts"]["counts"]["total"] == 1
