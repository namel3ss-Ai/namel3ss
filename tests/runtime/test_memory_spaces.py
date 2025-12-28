from hashlib import sha256
from pathlib import Path

from namel3ss.runtime.memory.contract import MemoryClock, MemoryIdGenerator, MemoryItemFactory, MemoryKind
from namel3ss.runtime.memory.events import EVENT_DECISION, EVENT_PREFERENCE
from namel3ss.runtime.memory.spaces import resolve_space_context
from namel3ss.runtime.memory_policy.defaults import default_contract
from namel3ss.runtime.memory_policy.evaluation import (
    PROMOTION_DENY_AUTHORITY,
    PROMOTION_DENY_POLICY,
    evaluate_border_read,
    evaluate_border_write,
    evaluate_promotion,
)


def test_space_context_resolution_prefers_identity_and_project_root():
    ctx = resolve_space_context(
        {"user": {"id": 7}},
        identity={"id": "user-9"},
        project_root="/tmp/namel3ss",
        app_path="/tmp/namel3ss/app.ai",
    )
    assert ctx.session_id == "7"
    assert ctx.user_id == "user-9"
    expected = sha256(Path("/tmp/namel3ss").resolve().as_posix().encode("utf-8")).hexdigest()[:12]
    assert ctx.project_id == expected
    assert ctx.store_key_for("session") == "session:7"


def test_space_context_falls_back_to_app_path():
    ctx = resolve_space_context({}, project_root=None, app_path="/tmp/namel3ss/app.ai")
    expected = sha256(Path("/tmp/namel3ss/app.ai").resolve().as_posix().encode("utf-8")).hexdigest()[:12]
    assert ctx.project_id == expected


def test_border_rules_default_policy():
    contract = default_contract(write_policy="normal", forget_policy="decay")
    assert evaluate_border_read(contract, space="session").allowed is True
    assert evaluate_border_write(contract, space="user").allowed is False


def test_promotion_decision_respects_authority_and_policy():
    contract = default_contract(write_policy="normal", forget_policy="decay")
    factory = MemoryItemFactory(clock=MemoryClock(), id_generator=MemoryIdGenerator())
    meta = {
        "event_type": EVENT_DECISION,
        "authority": "user_asserted",
        "authority_reason": "source:user",
        "space": "session",
        "owner": "s1",
    }
    item = factory.create(
        session="session:s1",
        kind=MemoryKind.SEMANTIC,
        text="We decided to ship weekly.",
        source="user",
        meta=meta,
    )
    decision = evaluate_promotion(
        contract,
        item=item,
        from_space="session",
        to_space="project",
        event_type=EVENT_DECISION,
    )
    assert decision.allowed is True

    low_meta = dict(meta)
    low_meta["event_type"] = EVENT_PREFERENCE
    low_item = factory.create(
        session="session:s1",
        kind=MemoryKind.SEMANTIC,
        text="I prefer weekly updates.",
        source="user",
        meta=low_meta,
    )
    denied = evaluate_promotion(
        contract,
        item=low_item,
        from_space="session",
        to_space="project",
        event_type=EVENT_PREFERENCE,
    )
    assert denied.allowed is False
    assert denied.reason == PROMOTION_DENY_AUTHORITY

    blocked = evaluate_promotion(
        contract,
        item=low_item,
        from_space="session",
        to_space="system",
        event_type=EVENT_PREFERENCE,
    )
    assert blocked.allowed is False
    assert blocked.reason == PROMOTION_DENY_POLICY
