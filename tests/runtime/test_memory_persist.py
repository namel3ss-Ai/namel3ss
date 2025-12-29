import hashlib
import json

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ai.mock_provider import MockProvider
from namel3ss.runtime.executor import Executor
from namel3ss.runtime.memory.contract import MemoryKind
from namel3ss.runtime.memory.manager import MemoryManager
from namel3ss.runtime.memory_budget.model import BudgetConfig
from namel3ss.runtime.memory_persist.paths import snapshot_paths
from namel3ss.runtime.memory_persist.reader import read_snapshot
from namel3ss.runtime.memory_persist.render import restore_failed_lines, wake_up_lines
from namel3ss.runtime.memory_persist.writer import build_snapshot_payload, serialize_snapshot, write_snapshot
from namel3ss.runtime.memory_trust.model import TrustRules
from tests.conftest import lower_ir_program


SOURCE = '''ai "assistant":
  provider is "mock"
  model is "test-model"
  memory:
    short_term is 2

spec is "1.0"

flow "demo":
  ask ai "assistant" with input: "Hello" as reply
  return reply
'''


def test_snapshot_store_order_is_stable(tmp_path):
    manager = MemoryManager()
    factory = manager._factory
    store_keys = ["session:owner:team", "session:owner:my"]
    for store_key in store_keys:
        phase, _ = manager._phases.ensure_phase(store_key)
        meta = {"phase_id": phase.phase_id}
        item = factory.create(
            session=store_key,
            kind=MemoryKind.SHORT_TERM,
            text=store_key,
            source="user",
            meta=meta,
        )
        manager.short_term.store_item(store_key, item)
    payload = build_snapshot_payload(manager, project_root=str(tmp_path), app_path=None)
    store_list = [store["store_key"] for store in payload["items"]["stores"]]
    assert store_list == sorted(store_list)
    payload_two = build_snapshot_payload(manager, project_root=str(tmp_path), app_path=None)
    assert serialize_snapshot(payload) == serialize_snapshot(payload_two)


def test_restore_round_trip(tmp_path):
    manager = MemoryManager()
    store_key, phase_id, proposal, packet = _seed_manager(manager)
    write_snapshot(manager, project_root=str(tmp_path), app_path=None)

    restored = MemoryManager()
    restored.ensure_restored(project_root=str(tmp_path), app_path=None)

    short_texts = [item.text for item in restored.short_term.all_items()]
    semantic_texts = [item.text for item in restored.semantic.all_items()]
    profile_texts = [item.text for item in restored.profile.all_items()]

    assert "Short term note" in short_texts
    assert "Semantic note" in semantic_texts
    assert "Ada" in profile_texts

    assert restored.agreements.get_pending(proposal.proposal_id) is not None
    assert restored.handoffs.get_packet(packet.packet_id) is not None

    assert restored._cache.get("cache-key", version=1) == {"value": "cached"}
    assert restored._cache_versions.get((store_key, "short_term")) == 3

    assert restored._budgets
    assert restored._budgets[0].max_items_short_term == 2

    assert isinstance(restored._trust_rules, TrustRules)

    assert phase_id in restored._ledger.phase_ids(store_key)


def test_checksum_mismatch_fails_restore(tmp_path):
    manager = MemoryManager()
    write_snapshot(manager, project_root=str(tmp_path), app_path=None)
    snapshot_path, checksum_path = snapshot_paths(project_root=str(tmp_path), app_path=None)
    assert snapshot_path is not None
    assert checksum_path is not None
    checksum_path.write_text("bad\n", encoding="utf-8")
    with pytest.raises(Namel3ssError, match="Checksum did not match"):
        read_snapshot(project_root=str(tmp_path), app_path=None)


def test_version_mismatch_fails_restore(tmp_path):
    manager = MemoryManager()
    payload = build_snapshot_payload(manager, project_root=str(tmp_path), app_path=None)
    payload["version"] = "memory_store_v0"
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    snapshot_path, checksum_path = snapshot_paths(project_root=str(tmp_path), app_path=None)
    assert snapshot_path is not None
    assert checksum_path is not None
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(data, encoding="utf-8")
    checksum = hashlib.sha256(data.encode("utf-8")).hexdigest()
    checksum_path.write_text(f"{checksum}\n", encoding="utf-8")
    with pytest.raises(Namel3ssError, match="Snapshot version does not match"):
        read_snapshot(project_root=str(tmp_path), app_path=None)


def test_wake_up_report_lines_are_stable():
    lines = wake_up_lines(
        restored=True,
        total_items=4,
        team_items=1,
        active_rules=2,
        pending_proposals=2,
        pending_handoffs=0,
        cache_entries=0,
        cache_enabled=True,
    )
    assert lines == [
        "Memory was restored.",
        "Total items are 4.",
        "Team memory loaded.",
        "Two rules active.",
        "Two proposals still waiting.",
        "No handoffs are waiting.",
        "Cache is empty.",
    ]
    assert _no_brackets(lines)


def test_restore_failed_lines_have_no_brackets():
    lines = restore_failed_lines(reason="Checksum did not match.", detail="Restore could not continue.")
    assert lines == [
        "Memory restore failed.",
        "Checksum did not match.",
        "Restore could not continue.",
    ]
    assert _no_brackets(lines)


def test_restore_wake_up_report_in_trace(tmp_path):
    app_path = tmp_path / "app.ai"
    app_path.write_text(SOURCE, encoding="utf-8")
    program = lower_ir_program(SOURCE)
    flow = program.flows[0]

    executor = Executor(
        flow,
        schemas={},
        ai_profiles=program.ais,
        ai_provider=MockProvider(),
        project_root=str(tmp_path),
        app_path=str(app_path),
    )
    executor.run()

    snapshot = read_snapshot(project_root=str(tmp_path), app_path=str(app_path))
    assert snapshot is not None
    stores = snapshot.get("items") or []
    assert stores
    store_key = stores[0]["store_key"]
    max_counter = _counter_for(snapshot.get("id_counters") or [], store_key, "short_term")

    executor_two = Executor(
        flow,
        schemas={},
        ai_profiles=program.ais,
        ai_provider=MockProvider(),
        project_root=str(tmp_path),
        app_path=str(app_path),
    )
    result = executor_two.run()
    trace = result.traces[0]
    event_types = [event["type"] for event in trace.canonical_events]
    assert "memory_wake_up_report" in event_types
    write_event = next(event for event in trace.canonical_events if event["type"] == "memory_write")
    ids = [
        item["id"]
        for item in write_event.get("written") or []
        if item.get("kind") == "short_term" and isinstance(item.get("id"), str)
    ]
    assert any(_counter_from_id(value) > max_counter for value in ids)


def _seed_manager(manager: MemoryManager):
    store_key = "session:owner:my"
    phase, _ = manager._phases.ensure_phase(store_key)
    meta = {
        "phase_id": phase.phase_id,
        "phase_started_at": phase.started_at,
        "phase_reason": phase.reason,
        "space": "session",
        "owner": "owner",
        "lane": "my",
    }
    short_item = manager._factory.create(
        session=store_key,
        kind=MemoryKind.SHORT_TERM,
        text="Short term note",
        source="user",
        meta=dict(meta),
    )
    manager.short_term.store_item(store_key, short_item)
    semantic_item = manager._factory.create(
        session=store_key,
        kind=MemoryKind.SEMANTIC,
        text="Semantic note",
        source="user",
        meta=dict(meta),
    )
    manager.semantic.store_item(store_key, semantic_item)
    profile_meta = dict(meta)
    profile_meta["key"] = "name"
    profile_item = manager._factory.create(
        session=store_key,
        kind=MemoryKind.PROFILE,
        text="Ada",
        source="user",
        meta=profile_meta,
    )
    manager.profile.store_item(store_key, profile_item)
    manager._ledger.start_phase(store_key, phase=phase, previous=None)
    manager._ledger.record_add(store_key, phase=phase, item=short_item)
    manager._ledger.record_add(store_key, phase=phase, item=semantic_item)
    manager._ledger.record_add(store_key, phase=phase, item=profile_item)

    proposal = manager.agreements.create_proposal(
        team_id="team-1",
        phase_id=phase.phase_id,
        memory_item=semantic_item,
        proposed_by="tester",
        reason_code="demo",
    )
    packet = manager.handoffs.create_packet(
        from_agent_id="agent-a",
        to_agent_id="agent-b",
        team_id="team-1",
        space="project",
        phase_id=phase.phase_id,
        created_by="tester",
        items=[semantic_item.id],
        summary_lines=["Handoff summary"],
    )
    manager._budgets = [
        BudgetConfig(
            space="session",
            lane="my",
            phase="any",
            owner="owner",
            max_items_short_term=2,
            cache_enabled=True,
            cache_max_entries=2,
            compaction_enabled=True,
        )
    ]
    manager._cache.set("cache-key", {"value": "cached"}, version=1)
    manager._cache_versions = {(store_key, "short_term"): 3}
    manager._trust_rules = TrustRules()
    return store_key, phase.phase_id, proposal, packet


def _counter_for(counters: list[dict], store_key: str, kind: str) -> int:
    for entry in counters:
        if entry.get("store_key") == store_key and entry.get("kind") == kind:
            return int(entry.get("counter", 0))
    return 0


def _counter_from_id(value: str) -> int:
    if not isinstance(value, str):
        return 0
    parts = value.split(":")
    if len(parts) < 3:
        return 0
    return int(parts[-1])


def _no_brackets(lines: list[str]) -> bool:
    for line in lines:
        for ch in "[](){}":
            if ch in line:
                return False
    return True
