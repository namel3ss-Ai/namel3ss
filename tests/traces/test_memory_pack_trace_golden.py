import json
from pathlib import Path

from namel3ss.runtime.memory_packs.format import MemoryPack, PackTrustSettings
from namel3ss.runtime.memory_packs.sources import OverrideEntry
from namel3ss.runtime.memory_packs.traces import (
    build_pack_loaded_event,
    build_pack_merged_event,
    build_pack_overrides_event,
)


def test_memory_pack_loaded_trace_golden():
    pack = MemoryPack(
        pack_id="base",
        pack_name="Base pack",
        pack_version="1.0.0",
        rules=["Only approvers can approve team proposals"],
        trust=PackTrustSettings(who_can_propose="contributor"),
        agreement=None,
        budgets=None,
        lanes=None,
        phase=None,
        source_path="pack.toml",
    )
    event = build_pack_loaded_event(pack=pack)
    fixture_path = Path("tests/fixtures/memory_pack_loaded_trace_golden.json")
    expected = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert event == expected


def test_memory_pack_merged_trace_golden():
    pack_one = MemoryPack(
        pack_id="base",
        pack_name="Base pack",
        pack_version="1.0.0",
        rules=None,
        trust=None,
        agreement=None,
        budgets=None,
        lanes=None,
        phase=None,
        source_path="pack.toml",
    )
    pack_two = MemoryPack(
        pack_id="team",
        pack_name="Team pack",
        pack_version="1.0.0",
        rules=None,
        trust=None,
        agreement=None,
        budgets=None,
        lanes=None,
        phase=None,
        source_path="pack.toml",
    )
    event = build_pack_merged_event(packs=[pack_one, pack_two])
    fixture_path = Path("tests/fixtures/memory_pack_merged_trace_golden.json")
    expected = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert event == expected


def test_memory_pack_overrides_trace_golden():
    overrides = [
        OverrideEntry(
            field="agreement.approval_count_required",
            from_source="pack base",
            to_source="local override",
        )
    ]
    event = build_pack_overrides_event(overrides=overrides)
    fixture_path = Path("tests/fixtures/memory_pack_overrides_trace_golden.json")
    expected = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert event == expected
