from namel3ss.runtime.memory.contract import MemoryClock, MemoryIdGenerator, MemoryItemFactory
from namel3ss.runtime.memory.events import EVENT_CONTEXT, build_dedupe_key
from namel3ss.runtime.memory.importance import importance_for_event
from namel3ss.runtime.memory.short_term import ShortTermMemory


def test_short_term_summary_item_created():
    factory = MemoryItemFactory(clock=MemoryClock(), id_generator=MemoryIdGenerator())
    memory = ShortTermMemory(factory=factory)
    items = []
    store_key = "session:s1:my"
    space = "session"
    owner = "s1"
    lane = "my"
    phase_id = "phase-1"
    for idx in range(3):
        text = f"turn {idx}"
        importance, reasons = importance_for_event(EVENT_CONTEXT, text, "user")
        meta = {
            "event_type": EVENT_CONTEXT,
            "importance_reason": reasons,
            "dedup_key": build_dedupe_key(EVENT_CONTEXT, text),
            "space": space,
            "owner": owner,
            "lane": lane,
            "visible_to": "me",
            "can_change": True,
            "phase_id": phase_id,
            "phase_started_at": 1,
            "phase_reason": "auto",
        }
        items.append(memory.record(store_key, text=text, source="user", importance=importance, meta=meta))

    summary, evicted, replaced = memory.summarize_if_needed(
        store_key,
        max_turns=2,
        phase_id=phase_id,
        space=space,
        owner=owner,
        lane=lane,
    )
    assert summary is not None
    assert [item.id for item in evicted] == [items[0].id]
    assert summary.meta["event_type"] == EVENT_CONTEXT
    assert summary.meta["summary_of"] == [items[0].id]
    assert replaced is None

    recalled = memory.recall(store_key, 2, phase_ids=[phase_id])
    assert recalled[0].id == summary.id
    assert [item.id for item in recalled[1:]] == [items[1].id, items[2].id]


def test_short_term_summary_replaces_prior_summary():
    factory = MemoryItemFactory(clock=MemoryClock(), id_generator=MemoryIdGenerator())
    memory = ShortTermMemory(factory=factory)
    store_key = "session:s1:my"
    space = "session"
    owner = "s1"
    lane = "my"
    phase_id = "phase-1"

    def record_turn(label: str) -> None:
        importance, reasons = importance_for_event(EVENT_CONTEXT, label, "user")
        meta = {
            "event_type": EVENT_CONTEXT,
            "importance_reason": reasons,
            "dedup_key": build_dedupe_key(EVENT_CONTEXT, label),
            "space": space,
            "owner": owner,
            "lane": lane,
            "visible_to": "me",
            "can_change": True,
            "phase_id": phase_id,
            "phase_started_at": 1,
            "phase_reason": "auto",
        }
        memory.record(store_key, text=label, source="user", importance=importance, meta=meta)

    for idx in range(3):
        record_turn(f"turn {idx}")
    summary1, _, replaced1 = memory.summarize_if_needed(
        store_key,
        max_turns=2,
        phase_id=phase_id,
        space=space,
        owner=owner,
        lane=lane,
    )
    assert summary1 is not None
    assert replaced1 is None

    record_turn("turn 3")
    record_turn("turn 4")
    summary2, _, replaced2 = memory.summarize_if_needed(
        store_key,
        max_turns=2,
        phase_id=phase_id,
        space=space,
        owner=owner,
        lane=lane,
    )
    assert summary2 is not None
    assert replaced2 is not None
    assert replaced2.id == summary1.id
