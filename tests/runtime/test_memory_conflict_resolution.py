from dataclasses import replace

from namel3ss.runtime.memory.contract import MemoryItem, MemoryKind, MemoryClock, MemoryIdGenerator, MemoryItemFactory
from namel3ss.runtime.memory.events import EVENT_CORRECTION, EVENT_FACT
from namel3ss.runtime.memory_policy.defaults import DEFAULT_AUTHORITY_ORDER
from namel3ss.runtime.memory_policy.evaluation import resolve_conflict
from namel3ss.runtime.memory_policy.model import (
    AUTHORITY_SYSTEM,
    AUTHORITY_USER,
)


def _factory():
    return MemoryItemFactory(clock=MemoryClock(), id_generator=MemoryIdGenerator())


def _item(factory, *, authority: str, event_type: str) -> MemoryItem:
    item = factory.create(
        session="s1",
        kind=MemoryKind.PROFILE,
        text="Ada",
        source="user",
        meta={"authority": authority, "event_type": event_type},
    )
    return item


def test_authority_wins_over_lower_authority():
    factory = _factory()
    existing = _item(factory, authority=AUTHORITY_SYSTEM, event_type=EVENT_FACT)
    incoming = _item(factory, authority=AUTHORITY_USER, event_type=EVENT_FACT)
    decision = resolve_conflict(existing, incoming, list(DEFAULT_AUTHORITY_ORDER))
    assert decision.winner.id == existing.id
    assert decision.rule == "authority"


def test_correction_overrides_higher_authority():
    factory = _factory()
    existing = _item(factory, authority=AUTHORITY_SYSTEM, event_type=EVENT_FACT)
    incoming = _item(factory, authority=AUTHORITY_USER, event_type=EVENT_CORRECTION)
    decision = resolve_conflict(existing, incoming, list(DEFAULT_AUTHORITY_ORDER))
    assert decision.winner.id == incoming.id
    assert decision.rule == "correction"


def test_importance_breaks_ties_after_recency():
    existing = MemoryItem(
        id="s1:profile:1",
        kind=MemoryKind.PROFILE,
        text="Ada",
        source="user",
        created_at=5,
        importance=1,
        meta={"authority": AUTHORITY_USER, "event_type": EVENT_FACT},
    )
    incoming = replace(existing, id="s1:profile:2", importance=4)
    decision = resolve_conflict(existing, incoming, list(DEFAULT_AUTHORITY_ORDER))
    assert decision.winner.id == incoming.id
    assert decision.rule == "importance"
