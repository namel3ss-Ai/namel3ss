from __future__ import annotations

import json
from pathlib import Path

from namel3ss.runtime.memory.contract import MemoryClock, MemoryIdGenerator, MemoryItemFactory
from namel3ss.runtime.memory.profile import ProfileMemory
from namel3ss.runtime.memory.semantic import SemanticMemory
from namel3ss.runtime.memory.short_term import ShortTermMemory
from namel3ss.runtime.memory_handoff.packet import build_packet_preview

FIXTURE_DIR = Path("tests/fixtures")


def test_handoff_preview_golden():
    clock = MemoryClock()
    ids = MemoryIdGenerator()
    factory = MemoryItemFactory(clock=clock, id_generator=ids)
    short_term = ShortTermMemory(factory=factory)
    semantic = SemanticMemory(factory=factory)
    profile = ProfileMemory(factory=factory)
    session = "session-1"

    decision = short_term.record(
        session,
        text="Agent decision",
        source="user",
        meta={"event_type": "decision", "lane": "agent"},
    )
    rule = semantic.record(
        session,
        text="Policy rule",
        source="system",
        meta={"event_type": "rule", "lane": "system"},
        dedupe_enabled=False,
    )
    pref = profile.set_fact(
        session,
        key="preference",
        value="Prefers email",
        source="user",
        meta={"event_type": "preference", "lane": "profile"},
        dedupe_enabled=False,
    )
    assert pref is not None

    item_ids = [decision.id, rule.id, pref.id]
    reasons = {
        decision.id: "decisions",
        rule.id: "rules",
        pref.id: "impact",
    }
    preview = build_packet_preview(
        short_term=short_term,
        semantic=semantic,
        profile=profile,
        item_ids=item_ids,
        reasons=reasons,
    )
    expected = json.loads((FIXTURE_DIR / "handoff_preview_golden.json").read_text(encoding="utf-8"))
    assert preview == expected
