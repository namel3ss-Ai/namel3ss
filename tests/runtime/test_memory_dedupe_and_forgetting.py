from namel3ss.runtime.memory.contract import MemoryClock, MemoryIdGenerator, MemoryItemFactory
from namel3ss.runtime.memory.events import EVENT_CONTEXT, EVENT_DECISION, build_dedupe_key
from namel3ss.runtime.memory.importance import importance_for_event
from namel3ss.runtime.memory.semantic import SemanticMemory
from namel3ss.runtime.memory_policy.defaults import default_contract


def _meta(event_type: str, text: str, source: str) -> tuple[int, dict]:
    importance, reasons = importance_for_event(event_type, text, source)
    return importance, {
        "event_type": event_type,
        "importance_reason": reasons,
        "dedup_key": build_dedupe_key(event_type, text),
        "space": "session",
        "owner": "s1",
        "lane": "my",
        "visible_to": "me",
        "can_change": True,
        "phase_id": "phase-1",
        "phase_started_at": 1,
        "phase_reason": "auto",
    }


def test_semantic_dedupe_merges_newest():
    factory = MemoryItemFactory(clock=MemoryClock(), id_generator=MemoryIdGenerator())
    memory = SemanticMemory(factory=factory)
    store_key = "session:s1:my"
    importance, meta = _meta(EVENT_DECISION, "We decided to ship weekly.", "user")
    memory.record(store_key, text="We decided to ship weekly.", source="user", importance=importance, meta=meta, dedupe_enabled=True)
    higher_importance, meta2 = _meta(EVENT_DECISION, "We decided to ship weekly.", "user")
    memory.record(
        store_key,
        text="We decided to ship weekly.",
        source="user",
        importance=higher_importance + 2,
        meta=meta2,
        dedupe_enabled=True,
    )
    snippets = memory._snippets[store_key]
    assert len(snippets) == 1
    assert snippets[0].importance == higher_importance + 2


def test_semantic_decay_forgets_old_context():
    factory = MemoryItemFactory(clock=MemoryClock(), id_generator=MemoryIdGenerator())
    memory = SemanticMemory(factory=factory)
    store_key = "session:s1:my"
    for idx in range(15):
        text = f"context {idx}"
        importance, meta = _meta(EVENT_CONTEXT, text, "user")
        memory.record(
            store_key,
            text=text,
            source="user",
            importance=importance,
            meta=meta,
            dedupe_enabled=False,
        )
    contract = default_contract(write_policy="normal", forget_policy="decay")
    now_tick = max(item.created_at for item in memory._snippets[store_key])
    memory.apply_retention(store_key, contract, now_tick)
    assert len(memory._snippets[store_key]) < 15
    recalled = memory.recall(store_key, "context", top_k=20)
    texts = {item.text for item in recalled}
    assert "context 0" not in texts
    assert "context 1" not in texts
