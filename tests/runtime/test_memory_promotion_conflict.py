from namel3ss.ir import nodes as ir
from namel3ss.runtime.memory.contract import MemoryKind
from namel3ss.runtime.memory.events import EVENT_FACT
from namel3ss.runtime.memory.manager import MemoryManager


def _ai_profile():
    return ir.AIDecl(
        name="assistant",
        model="gpt-4.1",
        provider="mock",
        system_prompt="hi",
        exposed_tools=[],
        memory=ir.AIMemory(short_term=1, semantic=True, profile=True, line=1, column=1),
        line=1,
        column=1,
    )


def test_promotion_conflict_keeps_higher_authority_fact():
    memory = MemoryManager()
    ai = _ai_profile()
    state = {"user": {"id": "1"}}
    space_ctx = memory.space_context(state)
    user_key = space_ctx.store_key_for("user", lane="my")
    existing_meta = {
        "event_type": EVENT_FACT,
        "importance_reason": ["event:fact"],
        "dedup_key": "fact:name",
        "authority": "system_imposed",
        "authority_reason": "seed",
        "space": "user",
        "owner": space_ctx.user_id,
        "lane": "my",
        "visible_to": "me",
        "can_change": True,
        "key": "name",
    }
    existing_item = memory._factory.create(
        session=user_key,
        kind=MemoryKind.PROFILE,
        text="Ada",
        source="system",
        importance=5,
        meta=existing_meta,
    )
    contract = memory.policy_contract_for(memory.policy_for(ai))
    memory.profile.store_item(
        user_key,
        existing_item,
        dedupe_enabled=True,
        authority_order=contract.authority_order,
    )
    _, events = memory.record_interaction_with_events(
        ai,
        state,
        "Remember this for me: My name is Ada Lovelace.",
        "ok",
        [],
    )
    facts = memory.profile._facts[user_key]
    assert facts["name"].text == "Ada"
    assert any(event["type"] == "memory_conflict" and event["rule"] == "authority" for event in events)
