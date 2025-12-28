from dataclasses import replace

from namel3ss.runtime.memory.contract import MemoryClock, MemoryIdGenerator, MemoryItemFactory, MemoryKind
from namel3ss.runtime.memory.events import EVENT_CONTEXT, EVENT_DECISION, EVENT_FACT
from namel3ss.runtime.memory_policy.defaults import DEFAULT_TTL_LIMIT, default_contract
from namel3ss.runtime.memory_policy.evaluation import apply_retention, evaluate_write


def _factory():
    return MemoryItemFactory(clock=MemoryClock(), id_generator=MemoryIdGenerator())


def test_write_policy_denies_semantic_when_none():
    contract = default_contract(write_policy="none", forget_policy="decay")
    item = _factory().create(
        session="s1",
        kind=MemoryKind.SEMANTIC,
        text="We decided to ship weekly.",
        source="user",
        meta={"event_type": EVENT_DECISION},
    )
    decision = evaluate_write(contract, item, event_type=EVENT_DECISION)
    assert decision.allowed is False
    assert decision.reason == "write_policy_none"


def test_allow_event_types_denies_non_matching():
    contract = replace(default_contract(write_policy="normal", forget_policy="decay"), allow_event_types=[EVENT_FACT])
    item = _factory().create(
        session="s1",
        kind=MemoryKind.SEMANTIC,
        text="We decided to ship weekly.",
        source="user",
        meta={"event_type": EVENT_DECISION},
    )
    decision = evaluate_write(contract, item, event_type=EVENT_DECISION)
    assert decision.allowed is False
    assert decision.reason == "policy_deny_event_type"


def test_privacy_denies_sensitive_text():
    contract = default_contract(write_policy="normal", forget_policy="decay")
    item = _factory().create(
        session="s1",
        kind=MemoryKind.SHORT_TERM,
        text="my password is 123",
        source="user",
        meta={"event_type": EVENT_CONTEXT},
    )
    decision = evaluate_write(contract, item, event_type=EVENT_CONTEXT)
    assert decision.allowed is False
    assert decision.reason == "privacy_deny_sensitive"


def test_retention_decay_forgets_old_context():
    contract = default_contract(write_policy="normal", forget_policy="decay")
    factory = _factory()
    items = []
    for idx in range(15):
        items.append(
            factory.create(
                session="s1",
                kind=MemoryKind.SEMANTIC,
                text=f"context {idx}",
                source="user",
                meta={"event_type": EVENT_CONTEXT},
            )
        )
    now_tick = max(item.created_at for item in items)
    kept, forgotten = apply_retention(items, contract, now_tick=now_tick)
    forgotten_texts = {item.text for item, reason in forgotten if reason == "decay"}
    assert "context 0" in forgotten_texts
    assert len(kept) < len(items)


def test_retention_ttl_expires():
    contract = default_contract(write_policy="normal", forget_policy="ttl")
    factory = _factory()
    item = factory.create(
        session="s1",
        kind=MemoryKind.SEMANTIC,
        text="context",
        source="user",
        meta={"event_type": EVENT_CONTEXT},
    )
    now_tick = item.created_at + DEFAULT_TTL_LIMIT + 1
    kept, forgotten = apply_retention([item], contract, now_tick=now_tick)
    assert not kept
    assert forgotten[0][1] == "ttl_expired"
