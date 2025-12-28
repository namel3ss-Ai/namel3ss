import json
from pathlib import Path

from namel3ss.runtime.memory_budget.measure import BudgetUsage
from namel3ss.runtime.memory_budget.model import BudgetConfig
from namel3ss.runtime.memory_budget.traces import build_budget_event
from namel3ss.runtime.memory_cache.traces import build_cache_event
from namel3ss.runtime.memory_compact.traces import build_compaction_event


def test_memory_budget_trace_golden():
    usage = BudgetUsage(
        store_key="session:owner:my",
        space="session",
        owner="owner",
        lane="my",
        phase_id="phase-1",
        short_term_count=10,
        semantic_count=0,
        profile_count=0,
        total_count=10,
        max_links_count=0,
        phase_count=1,
    )
    config = BudgetConfig(max_items_short_term=12, compaction_enabled=True)
    event = build_budget_event(
        ai_profile="assistant",
        session="sess-1",
        usage=usage,
        config=config,
    )
    fixture_path = Path("tests/fixtures/memory_budget_trace_golden.json")
    expected = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert event == expected


def test_memory_compaction_trace_golden():
    event = build_compaction_event(
        ai_profile="assistant",
        session="sess-1",
        space="session",
        lane="my",
        phase_id="phase-1",
        owner="owner",
        action="compact",
        reason="short_term_limit",
        items_removed_count=3,
        summary_written=True,
        summary_lines=["Summary line one.", "Summary line two."],
    )
    fixture_path = Path("tests/fixtures/memory_compaction_trace_golden.json")
    expected = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert event == expected


def test_memory_cache_hit_trace_golden():
    event = build_cache_event(
        ai_profile="assistant",
        session="sess-1",
        space="session",
        lane="my",
        phase_id="phase-1",
        hit=True,
    )
    fixture_path = Path("tests/fixtures/memory_cache_hit_trace_golden.json")
    expected = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert event == expected


def test_memory_cache_miss_trace_golden():
    event = build_cache_event(
        ai_profile="assistant",
        session="sess-1",
        space="session",
        lane="my",
        phase_id="phase-1",
        hit=False,
    )
    fixture_path = Path("tests/fixtures/memory_cache_miss_trace_golden.json")
    expected = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert event == expected
