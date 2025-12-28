from dataclasses import replace

from namel3ss.runtime.memory.contract import MemoryClock, MemoryIdGenerator, MemoryItemFactory, MemoryKind, MemoryItem
from namel3ss.runtime.memory.events import EVENT_DECISION, build_dedupe_key
from namel3ss.runtime.memory.recall_engine import _phase_ids_for_recall
from namel3ss.runtime.memory.semantic import SemanticMemory
from namel3ss.runtime.memory.policy import build_policy
from namel3ss.runtime.memory_timeline.diff import diff_phases
from namel3ss.runtime.memory_timeline.phase import PhaseInfo, PhaseRegistry, PhaseRequest
from namel3ss.runtime.memory_timeline.snapshot import PhaseLedger


def test_phase_registry_starts_new_phase_per_token():
    registry = PhaseRegistry(clock=MemoryClock())
    store_key = "session:s1:my"
    phase1, started1 = registry.ensure_phase(store_key)
    assert started1 is True
    assert phase1.phase_id == "phase-1"
    phase1_again, started_again = registry.ensure_phase(store_key)
    assert started_again is False
    assert phase1_again.phase_id == "phase-1"

    request = PhaseRequest(token="next", name=None, reason="manual")
    phase2, started2 = registry.ensure_phase(store_key, request=request, default_reason="auto")
    assert started2 is True
    assert phase2.phase_id == "phase-2"
    phase2_again, started2_again = registry.ensure_phase(store_key, request=request, default_reason="auto")
    assert started2_again is False
    assert phase2_again.phase_id == "phase-2"


def test_phase_recall_policy_ids_current_vs_history():
    registry = PhaseRegistry(clock=MemoryClock())
    store_key = "session:s1:my"
    phase1, _ = registry.ensure_phase(store_key)
    phase2, _ = registry.ensure_phase(
        store_key,
        request=PhaseRequest(token="phase-2", name=None, reason="manual"),
        default_reason="auto",
    )
    policy = build_policy(short_term=1, semantic=True, profile=False)
    assert _phase_ids_for_recall(registry, store_key, policy) == [phase2.phase_id]

    policy_history = replace(policy, allow_cross_phase_recall=True)
    assert _phase_ids_for_recall(registry, store_key, policy_history) == [phase2.phase_id, phase1.phase_id]


def test_semantic_recall_orders_by_phase():
    factory = MemoryItemFactory(clock=MemoryClock(), id_generator=MemoryIdGenerator())
    memory = SemanticMemory(factory=factory)
    store_key = "session:s1:my"
    meta1 = {
        "event_type": EVENT_DECISION,
        "dedup_key": build_dedupe_key(EVENT_DECISION, "We decided to ship weekly."),
        "phase_id": "phase-1",
    }
    meta2 = {
        "event_type": EVENT_DECISION,
        "dedup_key": build_dedupe_key(EVENT_DECISION, "We decided to ship weekly again."),
        "phase_id": "phase-2",
    }
    item1 = factory.create(session=store_key, kind=MemoryKind.SEMANTIC, text="weekly", source="user", meta=meta1)
    item2 = factory.create(session=store_key, kind=MemoryKind.SEMANTIC, text="weekly", source="user", meta=meta2)
    memory.store_item(store_key, item1, dedupe_enabled=False)
    memory.store_item(store_key, item2, dedupe_enabled=False)

    recalled = memory.recall(store_key, "weekly", top_k=5, phase_ids=["phase-2", "phase-1"])
    assert [item.meta.get("phase_id") for item in recalled[:2]] == ["phase-2", "phase-1"]


def test_phase_diff_reports_replacements():
    ledger = PhaseLedger()
    store_key = "session:s1:my"
    phase1 = PhaseInfo(phase_id="phase-1", phase_index=1, started_at=1, reason="auto", name=None)
    phase2 = PhaseInfo(phase_id="phase-2", phase_index=2, started_at=2, reason="manual", name=None)
    ledger.start_phase(store_key, phase=phase1, previous=None)

    before = MemoryItem(
        id="session:s1:my:profile:1",
        kind=MemoryKind.PROFILE,
        text="Ada",
        source="user",
        created_at=1,
        importance=0,
        meta={"dedup_key": "fact:name"},
    )
    ledger.record_add(store_key, phase=phase1, item=before)

    ledger.start_phase(store_key, phase=phase2, previous=phase1)
    after = MemoryItem(
        id="session:s1:my:profile:2",
        kind=MemoryKind.PROFILE,
        text="Ada Lovelace",
        source="user",
        created_at=2,
        importance=0,
        meta={"dedup_key": "fact:name"},
    )
    ledger.record_delete(store_key, phase=phase2, memory_id=before.id)
    ledger.record_add(store_key, phase=phase2, item=after)

    diff = diff_phases(ledger, store_key=store_key, from_phase_id="phase-1", to_phase_id="phase-2")
    assert len(diff.replaced) == 1
    assert diff.added == []
    assert diff.deleted == []
