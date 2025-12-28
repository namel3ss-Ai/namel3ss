from namel3ss.runtime.memory.contract import MemoryClock, MemoryIdGenerator, MemoryItemFactory, MemoryKind
from namel3ss.runtime.memory.profile import ProfileMemory
from namel3ss.runtime.memory.semantic import SemanticMemory
from namel3ss.runtime.memory.short_term import ShortTermMemory
from namel3ss.runtime.memory_budget.enforce import ACTION_COMPACT, REASON_SHORT_TERM_LIMIT, enforce_budget
from namel3ss.runtime.memory_budget.measure import BudgetUsage, measure_budget_usage, usage_for_scope
from namel3ss.runtime.memory_budget.model import BudgetConfig
from namel3ss.runtime.memory_budget.render import budget_lines
from namel3ss.runtime.memory_timeline.phase import PhaseRegistry


def test_budget_measurement_stable():
    clock = MemoryClock()
    ids = MemoryIdGenerator()
    factory = MemoryItemFactory(clock=clock, id_generator=ids)
    short_term = ShortTermMemory(factory=factory)
    semantic = SemanticMemory(factory=factory)
    profile = ProfileMemory(factory=factory)
    phases = PhaseRegistry(clock=clock)
    store_key = "session:owner:my"
    phase, _ = phases.ensure_phase(store_key)
    phases.start_phase(store_key, reason="manual")
    meta = {"phase_id": phase.phase_id}
    profile_meta = {"phase_id": phase.phase_id, "key": "name"}
    short_term.store_item(
        store_key,
        factory.create(session=store_key, kind=MemoryKind.SHORT_TERM, text="one", source="user", meta=meta),
    )
    semantic.store_item(
        store_key,
        factory.create(session=store_key, kind=MemoryKind.SEMANTIC, text="two", source="user", meta=meta),
    )
    profile.store_item(
        store_key,
        factory.create(session=store_key, kind=MemoryKind.PROFILE, text="three", source="user", meta=profile_meta),
    )
    usage = measure_budget_usage(short_term=short_term, semantic=semantic, profile=profile, phase_registry=phases)
    usage_repeat = measure_budget_usage(short_term=short_term, semantic=semantic, profile=profile, phase_registry=phases)
    assert usage == usage_repeat
    scoped = usage_for_scope(
        short_term=short_term,
        semantic=semantic,
        profile=profile,
        phase_registry=phases,
        store_key=store_key,
        phase_id=phase.phase_id,
    )
    assert scoped.short_term_count == 1
    assert scoped.semantic_count == 1
    assert scoped.profile_count == 1
    assert scoped.total_count == 3
    assert scoped.phase_count == 2


def test_enforce_budget_decision_stable():
    usage = BudgetUsage(
        store_key="session:owner:my",
        space="session",
        owner="owner",
        lane="my",
        phase_id="phase-1",
        short_term_count=2,
        semantic_count=0,
        profile_count=0,
        total_count=2,
        max_links_count=0,
        phase_count=1,
    )
    config = BudgetConfig(max_items_short_term=2, compaction_enabled=True)
    decision = enforce_budget(config=config, usage=usage, kind="short_term", incoming=1)
    assert decision.action == ACTION_COMPACT
    assert decision.reason == REASON_SHORT_TERM_LIMIT
    assert decision.over_by == 1


def test_budget_lines_have_no_brackets():
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
    lines = budget_lines(usage, config)
    assert lines
    assert _no_brackets(lines)


def _no_brackets(lines: list[str]) -> bool:
    for line in lines:
        for ch in "[](){}":
            if ch in line:
                return False
    return True
