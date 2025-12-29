from __future__ import annotations

from dataclasses import dataclass, replace

from namel3ss.runtime.memory.contract import MemoryItem, MemoryItemFactory
from namel3ss.runtime.memory_lanes.model import ensure_lane_meta
from namel3ss.runtime.memory_packs.sources import RuleSource, SOURCE_DEFAULT
from namel3ss.runtime.memory_policy.model import LanePolicy, PhasePolicy
from namel3ss.runtime.memory_rules.model import (
    ACTION_PROMOTE_TO_SYSTEM_LANE,
    RULE_SCOPE_SYSTEM,
    RULE_SCOPE_TEAM,
    RULE_STATUS_ACTIVE,
)
from namel3ss.runtime.memory_rules.parse import parse_rule_text
from namel3ss.runtime.memory_rules.store import build_rule_item, rule_lane_for_scope, rule_space_for_scope
from namel3ss.runtime.memory.semantic import SemanticMemory
from namel3ss.runtime.memory.spaces import SpaceContext, resolve_space_context
from namel3ss.runtime.memory_timeline.phase import PhaseRegistry
from namel3ss.runtime.memory_timeline.snapshot import PhaseLedger


PACK_RULE_META_KEY = "pack_rule"


@dataclass(frozen=True)
class PackRuleEntry:
    text: str
    scope: str
    source: str


@dataclass(frozen=True)
class PackRuleItem:
    item: MemoryItem
    store_key: str
    scope: str
    source: str


def apply_pack_rules(
    *,
    rules: list[str],
    rule_sources: list[RuleSource],
    semantic: SemanticMemory,
    factory: MemoryItemFactory,
    phase_registry: PhaseRegistry,
    phase_ledger: PhaseLedger,
    lanes: LanePolicy,
    phase: PhasePolicy,
    project_root: str | None,
    app_path: str | None,
) -> bool:
    if not project_root and not app_path:
        return False
    space_ctx = resolve_space_context(
        None,
        project_root=project_root,
        app_path=app_path,
    )
    desired = _desired_rule_entries(rules, rule_sources)
    existing = _existing_pack_rules(semantic)
    if _entries_match(existing, desired):
        return False
    _remove_pack_rules(
        existing,
        semantic=semantic,
        phase_registry=phase_registry,
        phase_ledger=phase_ledger,
        phase_policy=phase,
    )
    _write_pack_rules(
        desired,
        space_ctx=space_ctx,
        semantic=semantic,
        factory=factory,
        phase_registry=phase_registry,
        phase_ledger=phase_ledger,
        lanes=lanes,
        phase_policy=phase,
    )
    return True


def _desired_rule_entries(rules: list[str], rule_sources: list[RuleSource]) -> list[PackRuleEntry]:
    entries: list[PackRuleEntry] = []
    for idx, text in enumerate(rules):
        source = rule_sources[idx].source if idx < len(rule_sources) else SOURCE_DEFAULT
        entries.append(
            PackRuleEntry(
                text=str(text),
                scope=_scope_for_rule(text),
                source=source,
            )
        )
    return entries


def _existing_pack_rules(semantic: SemanticMemory) -> list[PackRuleItem]:
    items: list[PackRuleItem] = []
    for item in semantic.all_items():
        meta = item.meta or {}
        if not meta.get(PACK_RULE_META_KEY):
            continue
        store_key = _store_key_from_id(item.id)
        if not store_key:
            continue
        scope = str(meta.get("rule_scope") or RULE_SCOPE_TEAM)
        source = str(meta.get("rule_source") or SOURCE_DEFAULT)
        items.append(PackRuleItem(item=item, store_key=store_key, scope=scope, source=source))
    return items


def _entries_match(existing: list[PackRuleItem], desired: list[PackRuleEntry]) -> bool:
    existing_keys = sorted((entry.scope, entry.item.text, entry.source) for entry in existing)
    desired_keys = sorted((entry.scope, entry.text, entry.source) for entry in desired)
    return existing_keys == desired_keys


def _remove_pack_rules(
    items: list[PackRuleItem],
    *,
    semantic: SemanticMemory,
    phase_registry: PhaseRegistry,
    phase_ledger: PhaseLedger,
    phase_policy: PhasePolicy,
) -> None:
    by_store: dict[str, list[PackRuleItem]] = {}
    for entry in items:
        by_store.setdefault(entry.store_key, []).append(entry)
    for store_key, entries in by_store.items():
        phase = _ensure_phase_for_store(
            phase_registry=phase_registry,
            phase_ledger=phase_ledger,
            store_key=store_key,
            phase_policy=phase_policy,
        )
        for entry in sorted(entries, key=lambda record: record.item.id):
            removed = semantic.delete_item(store_key, entry.item.id)
            if removed:
                phase_ledger.record_delete(store_key, phase=phase, memory_id=removed.id)


def _write_pack_rules(
    entries: list[PackRuleEntry],
    *,
    space_ctx: SpaceContext,
    semantic: SemanticMemory,
    factory: MemoryItemFactory,
    phase_registry: PhaseRegistry,
    phase_ledger: PhaseLedger,
    lanes: LanePolicy,
    phase_policy: PhasePolicy,
) -> None:
    for entry in entries:
        space = rule_space_for_scope(entry.scope)
        lane = rule_lane_for_scope(entry.scope)
        owner = space_ctx.owner_for(space)
        store_key = space_ctx.store_key_for(space, lane=lane)
        phase = _ensure_phase_for_store(
            phase_registry=phase_registry,
            phase_ledger=phase_ledger,
            store_key=store_key,
            phase_policy=phase_policy,
        )
        rule_item, _spec = build_rule_item(
            factory=factory,
            store_key=store_key,
            text=entry.text,
            source=entry.source,
            scope=entry.scope,
            lane=lane,
            space=space,
            owner=owner,
            phase=phase,
            status=RULE_STATUS_ACTIVE,
            priority=0,
            created_by=entry.source,
        )
        meta = dict(rule_item.meta)
        meta[PACK_RULE_META_KEY] = True
        meta["rule_source"] = entry.source
        meta = ensure_lane_meta(
            meta,
            lane=lane,
            can_change=False,
            allow_team_change=lanes.team_can_change,
        )
        rule_item = replace(rule_item, meta=meta)
        stored, _conflict, deleted = semantic.store_item(
            store_key,
            rule_item,
            dedupe_enabled=True,
            authority_order=None,
        )
        if stored and stored.id == rule_item.id:
            phase_ledger.record_add(store_key, phase=phase, item=stored)
        if deleted:
            phase_ledger.record_delete(store_key, phase=phase, memory_id=deleted.id)


def _scope_for_rule(text: str) -> str:
    spec = parse_rule_text(text)
    if ACTION_PROMOTE_TO_SYSTEM_LANE in spec.actions:
        return RULE_SCOPE_SYSTEM
    return RULE_SCOPE_TEAM


def _store_key_from_id(memory_id: str) -> str | None:
    if not memory_id:
        return None
    parts = str(memory_id).split(":")
    if len(parts) < 3:
        return None
    return ":".join(parts[:-2])


def _ensure_phase_for_store(
    *,
    phase_registry: PhaseRegistry,
    phase_ledger: PhaseLedger,
    store_key: str,
    phase_policy: PhasePolicy,
) -> object:
    current = phase_registry.current(store_key)
    if current is not None:
        return current
    phase = phase_registry.start_phase(store_key, reason="pack")
    phase_ledger.start_phase(store_key, phase=phase, previous=None)
    phase_ledger.cleanup(store_key, phase_policy.max_phases)
    return phase


__all__ = ["PACK_RULE_META_KEY", "PackRuleEntry", "apply_pack_rules"]
