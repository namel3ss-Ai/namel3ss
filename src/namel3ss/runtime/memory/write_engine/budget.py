from __future__ import annotations

from dataclasses import dataclass

from namel3ss.runtime.memory.contract import MemoryItem, MemoryItemFactory
from namel3ss.runtime.memory.helpers import build_deleted_events
from namel3ss.runtime.memory.profile import ProfileMemory
from namel3ss.runtime.memory.semantic import SemanticMemory
from namel3ss.runtime.memory.short_term import ShortTermMemory
from namel3ss.runtime.memory_budget import (
    ACTION_ALLOW,
    ACTION_COMPACT,
    ACTION_DELETE_LOW_VALUE,
    ACTION_DENY_WRITE,
    BudgetConfig,
    BudgetDecision,
    enforce_budget,
    select_budget,
    usage_for_scope,
)
from namel3ss.runtime.memory_budget.traces import build_budget_event
from namel3ss.runtime.memory_compact import (
    CompactionResult,
    CompactionSelection,
    apply_compaction,
    build_compaction_event,
    select_compaction_items,
    summarize_items,
)
from namel3ss.runtime.memory_timeline.snapshot import PhaseLedger


MAX_COMPACT_ITEMS = 8
MIN_COMPACT_ITEMS = 2


@dataclass(frozen=True)
class BudgetOutcome:
    allowed: bool
    decision: BudgetDecision | None
    removed: list[MemoryItem]
    summary_item: MemoryItem | None


class BudgetEnforcer:
    def __init__(
        self,
        *,
        budgets: list[BudgetConfig],
        short_term: ShortTermMemory,
        semantic: SemanticMemory,
        profile: ProfileMemory,
        factory: MemoryItemFactory,
        phase_registry,
        phase_ledger: PhaseLedger,
        policy_snapshot: dict,
        phase_policy_snapshot: dict,
        contract,
        ai_profile: str,
        session: str,
        events: list[dict],
        written: list[MemoryItem],
    ) -> None:
        self._budgets = budgets
        self._short_term = short_term
        self._semantic = semantic
        self._profile = profile
        self._factory = factory
        self._phase_registry = phase_registry
        self._phase_ledger = phase_ledger
        self._policy_snapshot = policy_snapshot
        self._phase_policy_snapshot = phase_policy_snapshot
        self._contract = contract
        self._ai_profile = ai_profile
        self._session = session
        self._events = events
        self._written = written
        self._reserved: dict[tuple[str, str], bool] = {}

    def reserve(
        self,
        *,
        store_key: str,
        space: str,
        owner: str,
        lane: str,
        phase,
        kind: str,
        incoming: int,
    ) -> bool:
        outcome = self._apply_budget(
            store_key=store_key,
            space=space,
            owner=owner,
            lane=lane,
            phase=phase,
            kind=kind,
            incoming=incoming,
        )
        self._reserved[(store_key, kind)] = outcome.allowed
        return outcome.allowed

    def allow_write(
        self,
        *,
        store_key: str,
        space: str,
        owner: str,
        lane: str,
        phase,
        kind: str,
        incoming: int = 1,
    ) -> bool:
        cached = self._reserved.get((store_key, kind))
        if cached is not None:
            return cached
        outcome = self._apply_budget(
            store_key=store_key,
            space=space,
            owner=owner,
            lane=lane,
            phase=phase,
            kind=kind,
            incoming=incoming,
        )
        return outcome.allowed

    def _apply_budget(
        self,
        *,
        store_key: str,
        space: str,
        owner: str,
        lane: str,
        phase,
        kind: str,
        incoming: int,
    ) -> BudgetOutcome:
        phase_id = getattr(phase, "phase_id", "phase-unknown")
        config = select_budget(self._budgets, space=space, lane=lane, phase=phase_id, owner=owner)
        if config is None:
            return BudgetOutcome(allowed=True, decision=None, removed=[], summary_item=None)
        usage = usage_for_scope(
            short_term=self._short_term,
            semantic=self._semantic,
            profile=self._profile,
            phase_registry=self._phase_registry,
            store_key=store_key,
            phase_id=phase_id,
        )
        decision = enforce_budget(config=config, usage=usage, kind=kind, incoming=incoming)
        budget_event = build_budget_event(
            ai_profile=self._ai_profile,
            session=self._session,
            usage=usage,
            config=config,
        )
        if budget_event is not None:
            self._events.append(budget_event)
        if decision.action == ACTION_ALLOW:
            return BudgetOutcome(allowed=True, decision=decision, removed=[], summary_item=None)
        action = self._normalize_action(decision, kind=kind)
        selection = self._select_items(
            store_key=store_key,
            phase_id=phase_id,
            decision=decision,
            action=action,
            allow_delete_approved=self._allow_delete_approved(lane=lane),
        )
        if not selection.items:
            self._events.append(
                build_compaction_event(
                    ai_profile=self._ai_profile,
                    session=self._session,
                    space=space,
                    lane=lane,
                    phase_id=phase_id,
                    owner=owner,
                    action=ACTION_DENY_WRITE,
                    reason=decision.reason,
                    items_removed_count=0,
                    summary_written=False,
                    summary_lines=None,
                )
            )
            return BudgetOutcome(allowed=False, decision=decision, removed=[], summary_item=None)
        summary_item = None
        summary_lines = None
        if action == ACTION_COMPACT and len(selection.items) >= MIN_COMPACT_ITEMS:
            summary = summarize_items(selection.items)
            summary_lines = summary.lines
            result = apply_compaction(
                selection=selection,
                summary=summary,
                factory=self._factory,
                store_key=store_key,
                space=space,
                owner=owner,
                lane=lane,
                phase=phase,
                short_term=self._short_term,
                semantic=self._semantic,
                profile=self._profile,
                phase_ledger=self._phase_ledger,
                max_links_per_item=config.max_links_per_item,
            )
            summary_item = result.summary_item
            removed = result.removed
            if summary_item:
                self._written.append(summary_item)
            self._emit_removed_events(removed, space=space, owner=owner, phase=phase, reason="compacted")
        else:
            result = apply_compaction(
                selection=selection,
                summary=None,
                factory=self._factory,
                store_key=store_key,
                space=space,
                owner=owner,
                lane=lane,
                phase=phase,
                short_term=self._short_term,
                semantic=self._semantic,
                profile=self._profile,
                phase_ledger=self._phase_ledger,
                max_links_per_item=config.max_links_per_item,
            )
            removed = result.removed
            self._emit_removed_events(removed, space=space, owner=owner, phase=phase, reason="low_value")
        self._events.append(
            build_compaction_event(
                ai_profile=self._ai_profile,
                session=self._session,
                space=space,
                lane=lane,
                phase_id=phase_id,
                owner=owner,
                action=action,
                reason=decision.reason,
                items_removed_count=len(removed),
                summary_written=bool(summary_item),
                summary_lines=summary_lines,
            )
        )
        return BudgetOutcome(allowed=True, decision=decision, removed=removed, summary_item=summary_item)

    def _select_items(
        self,
        *,
        store_key: str,
        phase_id: str,
        decision: BudgetDecision,
        action: str,
        allow_delete_approved: bool,
    ) -> CompactionSelection:
        items = _items_for_store(store_key, self._short_term, self._semantic, self._profile)
        if not items:
            return CompactionSelection(items=[], reason_codes=[])
        if action == ACTION_DELETE_LOW_VALUE:
            max_remove = max(1, decision.over_by)
        else:
            max_remove = min(MAX_COMPACT_ITEMS, max(decision.over_by + 1, MIN_COMPACT_ITEMS))
        return select_compaction_items(
            items,
            phase_id=phase_id,
            target=decision.target,
            max_remove=max_remove,
            allow_delete_approved=allow_delete_approved,
        )

    def _allow_delete_approved(self, *, lane: str) -> bool:
        if lane != "team":
            return True
        return bool(getattr(self._contract.lanes, "team_can_change", True))

    def _emit_removed_events(self, removed: list[MemoryItem], *, space: str, owner: str, phase, reason: str) -> None:
        if not removed:
            return
        self._events.extend(
            build_deleted_events(
                self._ai_profile,
                self._session,
                space=space,
                owner=owner,
                phase=phase,
                removed=removed,
                reason=reason,
                policy_snapshot=self._phase_policy_snapshot,
                replaced_by=None,
            )
        )

    def _normalize_action(self, decision: BudgetDecision, *, kind: str) -> str:
        if kind == "profile" and decision.action == ACTION_COMPACT:
            return ACTION_DELETE_LOW_VALUE
        return decision.action


def _items_for_store(
    store_key: str,
    short_term: ShortTermMemory,
    semantic: SemanticMemory,
    profile: ProfileMemory,
) -> list[MemoryItem]:
    items: list[MemoryItem] = []
    items.extend([item for item in short_term.all_items() if _store_key_from_id(item.id) == store_key])
    items.extend([item for item in semantic.all_items() if _store_key_from_id(item.id) == store_key])
    items.extend([item for item in profile.all_items() if _store_key_from_id(item.id) == store_key])
    items.sort(key=lambda entry: entry.id)
    return items


def _store_key_from_id(memory_id: str) -> str | None:
    if not isinstance(memory_id, str):
        return None
    parts = memory_id.split(":")
    if len(parts) < 3:
        return None
    return ":".join(parts[:-2])


__all__ = ["BudgetEnforcer", "BudgetOutcome", "MAX_COMPACT_ITEMS", "MIN_COMPACT_ITEMS"]
