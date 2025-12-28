from namel3ss.runtime.memory.contract import MemoryClock, MemoryIdGenerator, MemoryItemFactory, MemoryKind
from namel3ss.runtime.memory.events import EVENT_CONTEXT, EVENT_DECISION
from namel3ss.runtime.memory_compact.select import select_compaction_items
from namel3ss.runtime.memory_compact.summarize import summarize_items
from namel3ss.runtime.memory_compact.traces import build_compaction_event


def test_compaction_selection_stable():
    clock = MemoryClock()
    factory = MemoryItemFactory(clock=clock, id_generator=MemoryIdGenerator())
    store_key = "session:owner:my"
    phase_id = "phase-1"
    items = [
        _item(factory, store_key, "alpha", phase_id=phase_id, lane="my", event_type=EVENT_CONTEXT),
        _item(factory, store_key, "beta", phase_id=phase_id, lane="my", event_type=EVENT_CONTEXT),
        _item(factory, store_key, "gamma", phase_id=phase_id, lane="team", event_type=EVENT_DECISION),
        _item(factory, store_key, "delta", phase_id=phase_id, lane="my", event_type=EVENT_CONTEXT),
    ]
    selection = select_compaction_items(
        items,
        phase_id=phase_id,
        target="short_term",
        max_remove=2,
        allow_delete_approved=True,
    )
    assert [item.id for item in selection.items] == [items[0].id, items[1].id]
    assert "context" in selection.reason_codes
    assert "low_importance" in selection.reason_codes
    assert "no_links" in selection.reason_codes


def test_summary_output_is_stable_and_bracketless():
    clock = MemoryClock()
    factory = MemoryItemFactory(clock=clock, id_generator=MemoryIdGenerator())
    store_key = "session:owner:my"
    items = [
        _item(factory, store_key, "note one [bracket]", phase_id="phase-1", lane="my", event_type=EVENT_CONTEXT),
        _item(factory, store_key, "note two (paren)", phase_id="phase-1", lane="my", event_type=EVENT_CONTEXT),
    ]
    summary = summarize_items(items)
    assert _no_brackets(summary.text)
    assert _no_brackets(summary.lines)
    for entry in summary.ledger:
        for value in entry.values():
            if isinstance(value, str):
                assert _no_brackets([value])
        preview_map = entry.get("link_preview_text")
        if isinstance(preview_map, dict):
            for value in preview_map.values():
                if isinstance(value, str):
                    assert _no_brackets([value])


def test_compaction_trace_lines_have_no_brackets():
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
    lines = event.get("lines") or []
    assert _no_brackets(lines)


def _item(factory: MemoryItemFactory, store_key: str, text: str, *, phase_id: str, lane: str, event_type: str):
    meta = {"phase_id": phase_id, "lane": lane, "event_type": event_type}
    return factory.create(
        session=store_key,
        kind=MemoryKind.SHORT_TERM,
        text=text,
        source="user",
        meta=meta,
    )


def _no_brackets(lines: list[str]) -> bool:
    for line in lines:
        for ch in "[](){}":
            if ch in line:
                return False
    return True
