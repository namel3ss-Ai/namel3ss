from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.memory.contract import (
    MemoryClock,
    MemoryIdGenerator,
    MemoryItemFactory,
    validate_memory_kind,
)
from namel3ss.runtime.memory_cache import MemoryCacheStore
from namel3ss.runtime.memory_cache.store import CacheEntry
from namel3ss.runtime.memory_budget.defaults import DEFAULT_CACHE_MAX_ENTRIES
from namel3ss.runtime.memory_handoff import HandoffStore
from namel3ss.runtime.memory_persist import (
    build_restore_failed_event,
    build_wake_up_report_event,
    read_snapshot,
    write_snapshot,
)
from namel3ss.runtime.memory_rules.model import RULE_STATUS_ACTIVE
from namel3ss.runtime.memory_rules.store import is_rule_item
from namel3ss.runtime.memory_lanes.model import LANE_TEAM
from namel3ss.runtime.memory.spaces import resolve_space_context
from namel3ss.runtime.memory_timeline.phase import PhaseRegistry
from namel3ss.runtime.memory_timeline.snapshot import PhaseLedger
from namel3ss.runtime.memory_agreement import ProposalStore
from namel3ss.runtime.memory.profile import ProfileMemory
from namel3ss.runtime.memory.semantic import SemanticMemory
from namel3ss.runtime.memory.short_term import ShortTermMemory


class MemoryManagerRestoreMixin:
    def persist(
        self,
        *,
        project_root: str | None = None,
        app_path: str | None = None,
        secret_values: list[str] | None = None,
    ) -> None:
        project_root, app_path = self._resolve_root(project_root, app_path)
        self._ensure_packs(project_root=project_root, app_path=app_path)
        write_snapshot(
            self,
            project_root=project_root,
            app_path=app_path,
            secret_values=secret_values,
        )

    def startup_events(
        self,
        *,
        project_root: str | None = None,
        app_path: str | None = None,
    ) -> list[dict]:
        project_root, app_path = self._resolve_root(project_root, app_path)
        self._ensure_restored(project_root=project_root, app_path=app_path)
        return self._consume_startup_events()

    def ensure_restored(
        self,
        *,
        project_root: str | None = None,
        app_path: str | None = None,
    ) -> None:
        project_root, app_path = self._resolve_root(project_root, app_path)
        self._ensure_restored(project_root=project_root, app_path=app_path)

    def _ensure_restored(self, *, project_root: str | None, app_path: str | None) -> None:
        if self._restore_state == "ready":
            return
        if self._restore_state == "failed":
            if self._restore_error:
                raise self._restore_error
            raise Namel3ssError("Memory restore failed.")
        if not project_root and not app_path:
            return
        self._ensure_packs(project_root=project_root, app_path=app_path)
        try:
            snapshot = read_snapshot(project_root=project_root, app_path=app_path)
        except Namel3ssError as err:
            self._restore_state = "failed"
            self._restore_error = Namel3ssError(f"Memory restore failed. {err}")
            self._startup_events.append(
                build_restore_failed_event(
                    project_id=self._project_id(project_root=project_root, app_path=app_path),
                    reason=str(err),
                    detail=None,
                )
            )
            raise self._restore_error
        if snapshot is None:
            self._apply_pack_setup(project_root=project_root, app_path=app_path)
            self._restore_state = "ready"
            self._startup_events.append(
                build_wake_up_report_event(
                    project_id=self._project_id(project_root=project_root, app_path=app_path),
                    restored=False,
                    **self._wake_up_counts(),
                )
            )
            return
        self._apply_snapshot(snapshot)
        self._apply_pack_setup(project_root=project_root, app_path=app_path)
        self._restore_state = "ready"
        self._startup_events.append(
            build_wake_up_report_event(
                project_id=self._project_id(project_root=project_root, app_path=app_path),
                restored=True,
                **self._wake_up_counts(),
            )
        )

    def _consume_startup_events(self) -> list[dict]:
        if not self._startup_events:
            return []
        events = list(self._startup_events)
        self._startup_events = []
        return events

    def _project_id(self, *, project_root: str | None, app_path: str | None) -> str:
        space_ctx = resolve_space_context(
            None,
            project_root=project_root,
            app_path=app_path,
        )
        return space_ctx.project_id

    def _wake_up_counts(self) -> dict:
        short_term_items = self.short_term.all_items()
        semantic_items = self.semantic.all_items()
        profile_items = self.profile.all_items()
        total_items = len(short_term_items) + len(semantic_items) + len(profile_items)
        team_items = _count_lane_items(short_term_items, LANE_TEAM)
        team_items += _count_lane_items(semantic_items, LANE_TEAM)
        team_items += _count_lane_items(profile_items, LANE_TEAM)
        active_rules = 0
        for item in semantic_items:
            if not is_rule_item(item):
                continue
            status = item.meta.get("rule_status")
            if status == RULE_STATUS_ACTIVE or status is None:
                active_rules += 1
        pending_proposals = len(getattr(self.agreements, "_pending_by_id", {}))
        pending_handoffs = 0
        for packet in getattr(self.handoffs, "_by_id", {}).values():
            if packet.status == "pending":
                pending_handoffs += 1
        cache_entries = self._cache.size() if self._cache else 0
        cache_enabled = True
        if self._budgets:
            cache_enabled = any(cfg.cache_enabled for cfg in self._budgets)
        return {
            "total_items": total_items,
            "team_items": team_items,
            "active_rules": active_rules,
            "pending_proposals": pending_proposals,
            "pending_handoffs": pending_handoffs,
            "cache_entries": cache_entries,
            "cache_enabled": cache_enabled,
        }

    def _apply_snapshot(self, snapshot: dict) -> None:
        clock = MemoryClock()
        ids = MemoryIdGenerator()
        factory = MemoryItemFactory(clock=clock, id_generator=ids)
        short_term = ShortTermMemory(factory=factory)
        semantic = SemanticMemory(factory=factory)
        profile = ProfileMemory(factory=factory)
        phase_registry = PhaseRegistry(clock=clock)
        phase_ledger = PhaseLedger()
        agreements = ProposalStore()
        handoffs = HandoffStore()
        cache = MemoryCacheStore(max_entries=DEFAULT_CACHE_MAX_ENTRIES)

        clock._tick = int(snapshot.get("clock_tick", 0))
        ids._counters = _decode_id_counters(snapshot.get("id_counters"))

        _apply_phase_registry(phase_registry, snapshot.get("phase_registry") or {})
        _apply_phase_ledger(phase_ledger, snapshot.get("phase_ledger") or {})

        _apply_items(short_term, semantic, profile, snapshot.get("items") or [])
        _apply_agreements(agreements, snapshot.get("agreements") or {})
        _apply_handoffs(handoffs, snapshot.get("handoffs") or {})

        budgets = list(snapshot.get("budgets") or [])
        cache_state = snapshot.get("cache") or {}
        cache_versions = _decode_cache_versions(snapshot.get("cache_versions") or [])
        _apply_cache(cache, cache_state)

        self._clock = clock
        self._ids = ids
        self._factory = factory
        self.short_term = short_term
        self.semantic = semantic
        self.profile = profile
        self._phases = phase_registry
        self._ledger = phase_ledger
        self.agreements = agreements
        self.handoffs = handoffs
        self._budgets = budgets
        self._cache = cache
        self._cache_versions = cache_versions
        self._trust_rules = snapshot.get("trust")


def _count_lane_items(items: list, lane: str) -> int:
    count = 0
    for item in items:
        meta = item.meta if hasattr(item, "meta") else {}
        if meta.get("lane") == lane:
            count += 1
    return count


def _decode_id_counters(counters: object) -> dict:
    if not isinstance(counters, list):
        return {}
    decoded: dict = {}
    for entry in counters:
        if not isinstance(entry, dict):
            continue
        store_key = entry.get("store_key")
        kind = entry.get("kind")
        counter = entry.get("counter")
        if not store_key or not kind:
            continue
        decoded[(str(store_key), validate_memory_kind(kind))] = int(counter)
    return decoded


def _apply_phase_registry(registry: PhaseRegistry, payload: dict) -> None:
    registry._counters = {key: int(value) for key, value in payload.get("counters", {}).items()}
    registry._current = {key: value for key, value in payload.get("current", {}).items()}
    registry._history = {key: list(value) for key, value in payload.get("history", {}).items()}
    registry._last_token = {key: str(value) for key, value in payload.get("last_token", {}).items()}


def _apply_phase_ledger(ledger: PhaseLedger, payload: dict) -> None:
    ledger._snapshots = payload.get("snapshots", {})
    ledger._order = {key: list(value) for key, value in payload.get("order", {}).items()}


def _apply_items(
    short_term: ShortTermMemory,
    semantic: SemanticMemory,
    profile: ProfileMemory,
    stores: list,
) -> None:
    for store in stores:
        store_key = store.get("store_key")
        if not store_key:
            continue
        for phase in store.get("phases") or []:
            phase_id = phase.get("phase_id") or "phase-unknown"
            messages = phase.get("short_term_messages") or []
            summaries = phase.get("short_term_summaries") or []
            for item in messages:
                short_term._messages.setdefault(store_key, {}).setdefault(phase_id, []).append(item)
            for item in summaries:
                short_term._summaries.setdefault(store_key, {})[phase_id] = item
            for item in phase.get("semantic") or []:
                semantic._snippets.setdefault(store_key, []).append(item)
            for item in phase.get("profile") or []:
                key = item.meta.get("key") if hasattr(item, "meta") else None
                if key:
                    profile._facts.setdefault(store_key, {})[key] = item


def _apply_agreements(store: ProposalStore, payload: dict) -> None:
    store._counter = int(payload.get("counter", 0))
    store._tick = int(payload.get("tick", 0))
    store._pending_by_id = {}
    store._pending_by_team = {}
    for proposal in payload.get("pending") or []:
        store._pending_by_id[proposal.proposal_id] = proposal
        store._pending_by_team.setdefault(proposal.team_id, {}).setdefault(proposal.phase_id, []).append(proposal)
    store._history = payload.get("history", {})


def _apply_handoffs(store: HandoffStore, payload: dict) -> None:
    store._counter = int(payload.get("counter", 0))
    store._tick = int(payload.get("tick", 0))
    store._by_id = {}
    store._by_team = {}
    for packet in payload.get("packets") or []:
        store._by_id[packet.packet_id] = packet
        store._by_team.setdefault(packet.team_id, {}).setdefault(packet.phase_id, []).append(packet)


def _decode_cache_versions(entries: list[dict]) -> dict[tuple[str, str], int]:
    decoded: dict[tuple[str, str], int] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        store_key = entry.get("store_key")
        kind = entry.get("kind")
        version = entry.get("version")
        if store_key and kind:
            decoded[(str(store_key), str(kind))] = int(version)
    return decoded


def _apply_cache(cache: MemoryCacheStore, payload: dict) -> None:
    cache._max_entries = int(payload.get("max_entries", 0))
    cache._counter = int(payload.get("counter", 0))
    cache._entries = {}
    for entry in payload.get("entries") or []:
        key = entry.get("key")
        cache_entry = entry.get("cache_entry")
        if not key or not isinstance(cache_entry, CacheEntry):
            continue
        cache._entries[str(key)] = cache_entry


__all__ = ["MemoryManagerRestoreMixin"]
