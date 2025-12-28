from namel3ss.runtime.memory.contract import MemoryClock, MemoryIdGenerator, MemoryItemFactory, MemoryKind
from namel3ss.runtime.memory.profile import ProfileMemory
from namel3ss.runtime.memory.semantic import SemanticMemory
from namel3ss.runtime.memory.short_term import ShortTermMemory
from namel3ss.runtime.memory_impact import compute_impact, render_change_preview, render_impact
from namel3ss.runtime.memory_links.model import (
    LINK_TYPE_CAUSED_BY,
    LINK_TYPE_CONFLICTS_WITH,
    LINK_TYPE_DEPENDS_ON,
    LINK_TYPE_PROMOTED_FROM,
    LINK_TYPE_REPLACED,
    LINK_TYPE_SUPPORTS,
)


def _memory_setup():
    clock = MemoryClock()
    ids = MemoryIdGenerator()
    factory = MemoryItemFactory(clock=clock, id_generator=ids)
    return factory, ShortTermMemory(factory=factory), SemanticMemory(factory=factory), ProfileMemory(factory=factory)


def _store_item(store, key, item):
    store.store_item(key, item)
    return item


def test_impact_direction_reverse_links():
    factory, short_term, semantic, profile = _memory_setup()
    store_key = "session:anon"
    target = factory.create(
        session=store_key,
        kind=MemoryKind.SEMANTIC,
        text="Target",
        source="user",
        meta={"space": "session", "phase_id": "phase-1"},
    )
    source = factory.create(
        session=store_key,
        kind=MemoryKind.SEMANTIC,
        text="Source",
        source="user",
        meta={
            "space": "session",
            "phase_id": "phase-1",
            "links": [
                {
                    "type": LINK_TYPE_DEPENDS_ON,
                    "to_id": target.id,
                    "reason_code": "depends_on",
                    "created_in_phase_id": "phase-1",
                }
            ],
            "link_preview_text": {target.id: "Target"},
        },
    )
    _store_item(semantic, store_key, target)
    _store_item(semantic, store_key, source)

    impact_on_target = compute_impact(
        memory_id=target.id,
        short_term=short_term,
        semantic=semantic,
        profile=profile,
        depth_limit=2,
        max_items=10,
    )
    impacted_ids = {item.memory_id for item in impact_on_target.items}
    assert source.id in impacted_ids

    impact_on_source = compute_impact(
        memory_id=source.id,
        short_term=short_term,
        semantic=semantic,
        profile=profile,
        depth_limit=2,
        max_items=10,
    )
    impacted_ids = {item.memory_id for item in impact_on_source.items}
    assert target.id not in impacted_ids


def test_impact_direction_forward_links():
    factory, short_term, semantic, profile = _memory_setup()
    store_key = "session:anon"
    old = factory.create(
        session=store_key,
        kind=MemoryKind.SEMANTIC,
        text="Old",
        source="user",
        meta={"space": "session", "phase_id": "phase-1"},
    )
    new = factory.create(
        session=store_key,
        kind=MemoryKind.SEMANTIC,
        text="New",
        source="user",
        meta={
            "space": "session",
            "phase_id": "phase-2",
            "links": [
                {
                    "type": LINK_TYPE_REPLACED,
                    "to_id": old.id,
                    "reason_code": "replaced",
                    "created_in_phase_id": "phase-2",
                }
            ],
            "link_preview_text": {old.id: "Old"},
        },
    )
    _store_item(semantic, store_key, old)
    _store_item(semantic, store_key, new)

    impact_on_new = compute_impact(
        memory_id=new.id,
        short_term=short_term,
        semantic=semantic,
        profile=profile,
        depth_limit=2,
        max_items=10,
    )
    impacted_ids = {item.memory_id for item in impact_on_new.items}
    assert old.id in impacted_ids

    impact_on_old = compute_impact(
        memory_id=old.id,
        short_term=short_term,
        semantic=semantic,
        profile=profile,
        depth_limit=2,
        max_items=10,
    )
    impacted_ids = {item.memory_id for item in impact_on_old.items}
    assert new.id not in impacted_ids


def test_impact_direction_bidir_links():
    factory, short_term, semantic, profile = _memory_setup()
    store_key = "session:anon"
    first = factory.create(
        session=store_key,
        kind=MemoryKind.SEMANTIC,
        text="First",
        source="user",
        meta={
            "space": "session",
            "phase_id": "phase-1",
            "links": [
                {
                    "type": LINK_TYPE_CONFLICTS_WITH,
                    "to_id": "session:anon:semantic:2",
                    "reason_code": "conflict",
                    "created_in_phase_id": "phase-1",
                }
            ],
            "link_preview_text": {"session:anon:semantic:2": "Second"},
        },
    )
    second = factory.create(
        session=store_key,
        kind=MemoryKind.SEMANTIC,
        text="Second",
        source="user",
        meta={"space": "session", "phase_id": "phase-1"},
    )
    _store_item(semantic, store_key, first)
    _store_item(semantic, store_key, second)

    impact_on_first = compute_impact(
        memory_id=first.id,
        short_term=short_term,
        semantic=semantic,
        profile=profile,
        depth_limit=2,
        max_items=10,
    )
    impacted_ids = {item.memory_id for item in impact_on_first.items}
    assert second.id in impacted_ids

    impact_on_second = compute_impact(
        memory_id=second.id,
        short_term=short_term,
        semantic=semantic,
        profile=profile,
        depth_limit=2,
        max_items=10,
    )
    impacted_ids = {item.memory_id for item in impact_on_second.items}
    assert first.id in impacted_ids


def test_impact_ordering_by_phase_space_id():
    factory, short_term, semantic, profile = _memory_setup()
    store_key = "session:anon"
    older = factory.create(
        session=store_key,
        kind=MemoryKind.SEMANTIC,
        text="Older",
        source="user",
        meta={"space": "project", "phase_id": "phase-1"},
    )
    newer = factory.create(
        session=store_key,
        kind=MemoryKind.SEMANTIC,
        text="Newer",
        source="user",
        meta={"space": "session", "phase_id": "phase-2"},
    )
    root = factory.create(
        session=store_key,
        kind=MemoryKind.SEMANTIC,
        text="Root",
        source="user",
        meta={
            "space": "session",
            "phase_id": "phase-2",
                "links": [
                    {
                        "type": LINK_TYPE_REPLACED,
                        "to_id": older.id,
                        "reason_code": "replaced",
                        "created_in_phase_id": "phase-2",
                    },
                    {
                        "type": LINK_TYPE_PROMOTED_FROM,
                        "to_id": newer.id,
                        "reason_code": "promoted",
                        "created_in_phase_id": "phase-2",
                    },
                ],
            "link_preview_text": {older.id: "Older", newer.id: "Newer"},
        },
    )
    _store_item(semantic, store_key, older)
    _store_item(semantic, store_key, newer)
    _store_item(semantic, store_key, root)

    impact = compute_impact(
        memory_id=root.id,
        short_term=short_term,
        semantic=semantic,
        profile=profile,
        depth_limit=2,
        max_items=10,
    )
    ordered_ids = [item.memory_id for item in impact.items]
    assert ordered_ids == [older.id, newer.id]


def test_impact_loop_avoidance_and_bracketless_render():
    factory, short_term, semantic, profile = _memory_setup()
    store_key = "session:anon"
    first = factory.create(
        session=store_key,
        kind=MemoryKind.SEMANTIC,
        text="First [demo]",
        source="user",
        meta={
            "space": "session",
            "phase_id": "phase-1",
            "links": [
                {
                    "type": LINK_TYPE_PROMOTED_FROM,
                    "to_id": "session:anon:semantic:2",
                    "reason_code": "promoted",
                    "created_in_phase_id": "phase-1",
                }
            ],
            "link_preview_text": {"session:anon:semantic:2": "Second {demo}"},
        },
    )
    second = factory.create(
        session=store_key,
        kind=MemoryKind.SEMANTIC,
        text="Second {demo}",
        source="user",
        meta={
            "space": "session",
            "phase_id": "phase-1",
            "links": [
                {
                    "type": LINK_TYPE_PROMOTED_FROM,
                    "to_id": first.id,
                    "reason_code": "promoted",
                    "created_in_phase_id": "phase-1",
                }
            ],
            "link_preview_text": {first.id: "First [demo]"},
        },
    )
    _store_item(semantic, store_key, first)
    _store_item(semantic, store_key, second)

    impact = compute_impact(
        memory_id=first.id,
        short_term=short_term,
        semantic=semantic,
        profile=profile,
        depth_limit=2,
        max_items=10,
    )
    assert len(impact.items) == 1

    rendered = render_impact(impact, depth_used=2)
    preview_lines = render_change_preview(impact, change_kind="replace")
    all_lines = rendered.lines + rendered.path_lines + preview_lines
    assert all(ch not in line for line in all_lines for ch in "[]{}()")
