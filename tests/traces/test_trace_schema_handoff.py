from namel3ss.traces.builders import (
    build_memory_agent_briefing,
    build_memory_handoff_applied,
    build_memory_handoff_created,
    build_memory_handoff_rejected,
)
from namel3ss.traces.schema import TRACE_VERSION, TraceEventType


def test_memory_handoff_trace_events():
    created = build_memory_handoff_created(
        ai_profile="assistant",
        session="sess-1",
        packet_id="handoff-1",
        from_agent_id="agent-a",
        to_agent_id="agent-b",
        team_id="team-1",
        phase_id="phase-1",
        title="Memory handoff created",
        lines=["Handoff packet created."],
    )
    assert created["type"] == TraceEventType.MEMORY_HANDOFF_CREATED
    assert created["trace_version"] == TRACE_VERSION
    assert created["packet_id"] == "handoff-1"

    applied = build_memory_handoff_applied(
        ai_profile="assistant",
        session="sess-1",
        packet_id="handoff-1",
        from_agent_id="agent-a",
        to_agent_id="agent-b",
        item_count=2,
        title="Memory handoff applied",
        lines=["Handoff packet applied."],
    )
    assert applied["type"] == TraceEventType.MEMORY_HANDOFF_APPLIED
    assert applied["item_count"] == 2

    rejected = build_memory_handoff_rejected(
        ai_profile="assistant",
        session="sess-1",
        packet_id="handoff-1",
        from_agent_id="agent-a",
        to_agent_id="agent-b",
        title="Memory handoff rejected",
        lines=["Handoff packet rejected."],
    )
    assert rejected["type"] == TraceEventType.MEMORY_HANDOFF_REJECTED

    briefing = build_memory_agent_briefing(
        ai_profile="assistant",
        session="sess-1",
        packet_id="handoff-1",
        to_agent_id="agent-b",
        title="Agent briefing",
        lines=["Here is what you need to know."],
    )
    assert briefing["type"] == TraceEventType.MEMORY_AGENT_BRIEFING
    assert briefing["packet_id"] == "handoff-1"
