from namel3ss.runtime.memory.contract import MemoryClock, MemoryIdGenerator, MemoryItemFactory, MemoryKind
from namel3ss.runtime.memory.events import EVENT_CONTEXT, EVENT_DECISION
from namel3ss.runtime.memory.helpers import authority_for_source, build_meta
from namel3ss.runtime.memory.importance import importance_for_event
from namel3ss.runtime.memory.manager import MemoryManager
from namel3ss.runtime.memory.spaces import SPACE_PROJECT
from namel3ss.runtime.memory_lanes.model import LANE_AGENT, LANE_TEAM, agent_lane_key
from namel3ss.runtime.memory_handoff import HandoffSelection, apply_handoff_packet, briefing_lines, select_handoff_items
from namel3ss.runtime.memory_handoff.store import HandoffStore
from namel3ss.runtime.memory_agreement.model import Proposal
from namel3ss.runtime.memory_links import LINK_TYPE_CONFLICTS_WITH
from namel3ss.runtime.memory_policy.defaults import DEFAULT_AUTHORITY_ORDER
from namel3ss.runtime.memory_rules.model import RULE_SCOPE_TEAM, RULE_STATUS_ACTIVE, Rule
from tests.conftest import lower_ir_program


def _factory() -> MemoryItemFactory:
    return MemoryItemFactory(clock=MemoryClock(), id_generator=MemoryIdGenerator())


def _rule(text: str, *, rule_id: str, priority: int = 0) -> Rule:
    return Rule(
        rule_id=rule_id,
        text=text,
        scope=RULE_SCOPE_TEAM,
        lane="team",
        phase_id="phase-1",
        status=RULE_STATUS_ACTIVE,
        created_by="tester",
        created_at=1,
        priority=priority,
    )


def test_agent_lane_privacy_in_recall():
    program = lower_ir_program(
        '''ai "assistant":
  provider is "mock"
  model is "mock-model"
  memory:
    short_term is 1
    semantic is true
    profile is false
'''
    )
    ai = program.ais["assistant"]
    memory = MemoryManager()
    identity = {"id": "owner-1"}
    state: dict = {}
    space_ctx = memory.space_context(state, identity=identity)
    owner = space_ctx.owner_for(SPACE_PROJECT)
    authority, authority_reason = authority_for_source("user")
    importance, reasons = importance_for_event(EVENT_DECISION, "Decision A", "user")
    store_key_a = agent_lane_key(space_ctx, space=SPACE_PROJECT, agent_id="agent-a")
    phase_a, _started = memory._phases.ensure_phase(store_key_a)
    meta_a = build_meta(
        EVENT_DECISION,
        reasons,
        "Decision A",
        authority=authority,
        authority_reason=authority_reason,
        space=SPACE_PROJECT,
        owner=owner,
        lane=LANE_AGENT,
        agent_id="agent-a",
        phase=phase_a,
    )
    item_a = memory._factory.create(
        session=store_key_a,
        kind=MemoryKind.SEMANTIC,
        text="Decision A",
        source="user",
        importance=importance,
        meta=meta_a,
    )
    memory.semantic.store_item(store_key_a, item_a, dedupe_enabled=False)

    importance, reasons = importance_for_event(EVENT_DECISION, "Decision B", "user")
    store_key_b = agent_lane_key(space_ctx, space=SPACE_PROJECT, agent_id="agent-b")
    phase_b, _started = memory._phases.ensure_phase(store_key_b)
    meta_b = build_meta(
        EVENT_DECISION,
        reasons,
        "Decision B",
        authority=authority,
        authority_reason=authority_reason,
        space=SPACE_PROJECT,
        owner=owner,
        lane=LANE_AGENT,
        agent_id="agent-b",
        phase=phase_b,
    )
    item_b = memory._factory.create(
        session=store_key_b,
        kind=MemoryKind.SEMANTIC,
        text="Decision B",
        source="user",
        importance=importance,
        meta=meta_b,
    )
    memory.semantic.store_item(store_key_b, item_b, dedupe_enabled=False)

    context, _events, _meta = memory.recall_context_with_events(
        ai,
        "Decision",
        state,
        identity=identity,
        agent_id="agent-a",
    )
    agent_ids = {item["meta"].get("agent_id") for item in context["semantic"]}
    assert agent_ids == {"agent-a"}

    context, _events, _meta = memory.recall_context_with_events(
        ai,
        "Decision",
        state,
        identity=identity,
        agent_id="agent-b",
    )
    agent_ids = {item["meta"].get("agent_id") for item in context["semantic"]}
    assert agent_ids == {"agent-b"}

    context, _events, _meta = memory.recall_context_with_events(
        ai,
        "Decision",
        state,
        identity=identity,
        agent_id=None,
    )
    assert context["semantic"] == []


def test_handoff_selection_is_deterministic_and_bracketless():
    factory = _factory()
    decision_old = factory.create(
        session="store",
        kind=MemoryKind.SEMANTIC,
        text="Decision old",
        source="user",
        meta={"event_type": EVENT_DECISION},
    )
    conflict_item = factory.create(
        session="store",
        kind=MemoryKind.SEMANTIC,
        text="Conflict",
        source="user",
        meta={
            "event_type": EVENT_CONTEXT,
            "links": [{"type": LINK_TYPE_CONFLICTS_WITH, "to_id": "older"}],
        },
    )
    impact_item = factory.create(
        session="store",
        kind=MemoryKind.SEMANTIC,
        text="Impact",
        source="user",
        meta={"event_type": EVENT_CONTEXT, "impact_warning": True},
    )
    decision_new = factory.create(
        session="store",
        kind=MemoryKind.SEMANTIC,
        text="Decision new",
        source="user",
        meta={"event_type": EVENT_DECISION},
    )
    proposal_item = factory.create(
        session="store",
        kind=MemoryKind.SEMANTIC,
        text="Proposal",
        source="user",
        meta={"event_type": EVENT_CONTEXT},
    )
    proposal = Proposal(
        proposal_id="proposal-1",
        memory_item=proposal_item,
        team_id="team-1",
        phase_id="phase-1",
        status="pending",
        proposed_by="user",
        proposed_at=1,
    )
    rules = [
        _rule("Only approvers can approve team proposals", rule_id="rule-1", priority=0),
        _rule("Only contributors can create handoff packets", rule_id="rule-2", priority=1),
    ]
    selection = select_handoff_items(
        agent_items=[decision_new, conflict_item],
        team_items=[decision_old, impact_item],
        proposals=[proposal],
        rules=rules,
    )
    assert selection.item_ids == [
        decision_new.id,
        decision_old.id,
        proposal_item.id,
        conflict_item.id,
        "rule-2",
        "rule-1",
        impact_item.id,
    ]
    assert selection.summary_lines == [
        "Handoff packet summary.",
        "Decision items count is 2.",
        "Pending proposals count is 1.",
        "Conflicts count is 1.",
        "Active rules count is 2.",
        "Impact warnings count is 1.",
    ]
    for line in selection.summary_lines:
        assert all(ch not in line for ch in "[]{}()")


def test_handoff_apply_copies_items_and_preserves_previews():
    program = lower_ir_program(
        '''ai "assistant":
  provider is "mock"
  model is "mock-model"
  memory:
    short_term is 1
    semantic is true
    profile is false
'''
    )
    ai = program.ais["assistant"]
    memory = MemoryManager()
    identity = {"id": "owner-1"}
    state: dict = {}
    space_ctx = memory.space_context(state, identity=identity)
    owner = space_ctx.owner_for(SPACE_PROJECT)
    authority, authority_reason = authority_for_source("user")

    from_key = agent_lane_key(space_ctx, space=SPACE_PROJECT, agent_id="agent-a")
    team_key = space_ctx.store_key_for(SPACE_PROJECT, lane=LANE_TEAM)
    target_key = agent_lane_key(space_ctx, space=SPACE_PROJECT, agent_id="agent-b")
    target_phase, _started = memory._phases.ensure_phase(target_key)

    importance, reasons = importance_for_event(EVENT_DECISION, "Agent decision", "user")
    meta_agent = build_meta(
        EVENT_DECISION,
        reasons,
        "Agent decision",
        authority=authority,
        authority_reason=authority_reason,
        space=SPACE_PROJECT,
        owner=owner,
        lane=LANE_AGENT,
        agent_id="agent-a",
    )
    meta_agent["links"] = [{"type": LINK_TYPE_CONFLICTS_WITH, "to_id": "older"}]
    meta_agent["link_preview_text"] = {"older": "Old [detail]"}
    item_agent = memory._factory.create(
        session=from_key,
        kind=MemoryKind.SEMANTIC,
        text="Agent decision",
        source="user",
        importance=importance,
        meta=meta_agent,
    )
    stored_agent, _conflict, _deleted = memory.semantic.store_item(from_key, item_agent, dedupe_enabled=False)

    importance, reasons = importance_for_event(EVENT_DECISION, "Team decision", "user")
    meta_team = build_meta(
        EVENT_DECISION,
        reasons,
        "Team decision",
        authority=authority,
        authority_reason=authority_reason,
        space=SPACE_PROJECT,
        owner=owner,
        lane=LANE_TEAM,
    )
    item_team = memory._factory.create(
        session=team_key,
        kind=MemoryKind.SEMANTIC,
        text="Team decision",
        source="user",
        importance=importance,
        meta=meta_team,
    )
    stored_team, _conflict, _deleted = memory.semantic.store_item(team_key, item_team, dedupe_enabled=False)

    store = HandoffStore()
    packet = store.create_packet(
        from_agent_id="agent-a",
        to_agent_id="agent-b",
        team_id="team-1",
        space=SPACE_PROJECT,
        phase_id="phase-1",
        created_by="owner-1",
        items=[stored_agent.id, stored_team.id],
        summary_lines=["Here is what you need to know."],
    )
    applied = apply_handoff_packet(
        packet=packet,
        short_term=memory.short_term,
        semantic=memory.semantic,
        profile=memory.profile,
        factory=memory._factory,
        target_store_key=target_key,
        target_phase=target_phase,
        space=SPACE_PROJECT,
        owner=owner,
        agent_id="agent-b",
        allow_team_change=True,
        phase_ledger=memory._ledger,
        dedupe_enabled=False,
        authority_order=list(DEFAULT_AUTHORITY_ORDER),
    )
    assert len(applied) == 2
    stored = memory.semantic.items_for_store(target_key)
    assert len(stored) == 2
    for item in stored:
        meta = item.meta or {}
        assert meta.get("lane") == LANE_AGENT
        assert meta.get("agent_id") == "agent-b"
        assert meta.get("handoff_packet_id") == packet.packet_id
        assert meta.get("handoff_from_agent") == "agent-a"
        assert meta.get("handoff_to_agent") == "agent-b"
        assert "links" not in meta
        assert "link_preview_text" not in meta
    handoff_item = next(item for item in stored if item.text == "Agent decision")
    previews = handoff_item.meta.get("handoff_link_previews", [])
    assert previews
    assert all(ch not in previews[0] for ch in "[]{}()")
    original = memory.semantic.get_item(from_key, stored_agent.id)
    assert original is not None
    assert "links" in original.meta


def test_briefing_lines_are_bracketless():
    selection = HandoffSelection(
        item_ids=["id-1"],
        summary_lines=[],
        decision_count=1,
        proposal_count=0,
        conflict_count=0,
        rules_count=0,
        impact_count=0,
    )
    lines = briefing_lines(selection)
    for line in lines:
        assert all(ch not in line for ch in "[]{}()")


def test_handoff_store_orders_by_created_at():
    store = HandoffStore()
    packet_a = store.create_packet(
        from_agent_id="agent-a",
        to_agent_id="agent-b",
        team_id="team-1",
        space=SPACE_PROJECT,
        phase_id="phase-1",
        created_by="owner-1",
        items=["id-1"],
        summary_lines=["Summary one."],
    )
    packet_b = store.create_packet(
        from_agent_id="agent-b",
        to_agent_id="agent-a",
        team_id="team-1",
        space=SPACE_PROJECT,
        phase_id="phase-1",
        created_by="owner-1",
        items=["id-2"],
        summary_lines=["Summary two."],
    )
    packets = store.list_packets("team-1")
    assert [packet.packet_id for packet in packets] == [packet_a.packet_id, packet_b.packet_id]
