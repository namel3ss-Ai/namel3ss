from namel3ss.ir import nodes as ir
from namel3ss.runtime.memory.manager import MemoryManager


def _ai_profile():
    return ir.AIDecl(
        name="assistant",
        model="gpt-4.1",
        provider="mock",
        system_prompt=None,
        exposed_tools=[],
        memory=ir.AIMemory(short_term=1, semantic=False, profile=True, line=1, column=1),
        line=1,
        column=1,
    )


def test_correction_overwrites_profile_fact():
    memory = MemoryManager()
    ai = _ai_profile()
    state = {}
    memory.record_interaction(ai, state, "My name is Ada.", "ok", [])
    memory.record_interaction(ai, state, "Actually, my name is Ada Lovelace.", "ok", [])
    facts = memory.profile.recall("session:anonymous")
    assert len(facts) == 1
    assert facts[0].text == "Ada Lovelace"
    assert facts[0].meta["event_type"] == "correction"
