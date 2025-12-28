import json
from pathlib import Path

from namel3ss.runtime.memory_handoff.model import HANDOFF_STATUS_PENDING, HandoffPacket
from namel3ss.runtime.memory_handoff.render import briefing_lines
from namel3ss.runtime.memory_handoff.select import HandoffSelection
from namel3ss.runtime.memory_handoff.traces import (
    build_agent_briefing_event,
    build_handoff_applied_event,
    build_handoff_created_event,
    build_handoff_rejected_event,
)


def test_memory_handoff_trace_golden():
    selection = HandoffSelection(
        item_ids=["memory-1", "memory-2"],
        summary_lines=[],
        decision_count=1,
        proposal_count=1,
        conflict_count=0,
        rules_count=2,
        impact_count=1,
    )
    summary_lines = briefing_lines(selection)
    packet = HandoffPacket(
        packet_id="handoff-1",
        from_agent_id="agent-a",
        to_agent_id="agent-b",
        team_id="team-1",
        space="project",
        phase_id="phase-1",
        created_by="owner-1",
        created_at=1,
        items=list(selection.item_ids),
        summary_lines=summary_lines,
        status=HANDOFF_STATUS_PENDING,
    )
    events = [
        build_handoff_created_event(ai_profile="assistant", session="sess-1", packet=packet),
        build_handoff_applied_event(ai_profile="assistant", session="sess-1", packet=packet, item_count=2),
        build_handoff_rejected_event(ai_profile="assistant", session="sess-1", packet=packet),
        build_agent_briefing_event(ai_profile="assistant", session="sess-1", packet=packet),
    ]
    fixture_path = Path("tests/fixtures/memory_handoff_trace_golden.json")
    expected = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert events == expected
