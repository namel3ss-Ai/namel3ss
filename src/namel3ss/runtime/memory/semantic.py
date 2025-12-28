from __future__ import annotations

from dataclasses import replace
from typing import Dict, List, Optional

from namel3ss.runtime.memory.contract import MemoryItem, MemoryItemFactory, MemoryKind
from namel3ss.runtime.memory.events import EVENT_CONTEXT, normalize_text
from namel3ss.runtime.memory_policy.defaults import DEFAULT_AUTHORITY_ORDER
from namel3ss.runtime.memory_policy.evaluation import ConflictDecision, apply_retention, resolve_conflict


class SemanticMemory:
    def __init__(self, *, factory: MemoryItemFactory) -> None:
        self._factory = factory
        self._snippets: Dict[str, List[MemoryItem]] = {}

    def record(
        self,
        store_key: str,
        *,
        text: str,
        source: str,
        importance: int = 0,
        meta: Optional[dict] = None,
        dedupe_enabled: bool = True,
        authority_order: Optional[list[str]] = None,
    ) -> MemoryItem:
        item = self._factory.create(
            session=store_key,
            kind=MemoryKind.SEMANTIC,
            text=text,
            source=source,
            importance=importance,
            meta=meta or {},
        )
        stored, _, _ = self.store_item(
            store_key,
            item,
            dedupe_enabled=dedupe_enabled,
            authority_order=authority_order or list(DEFAULT_AUTHORITY_ORDER),
        )
        return stored

    def store_item(
        self,
        store_key: str,
        item: MemoryItem,
        *,
        dedupe_enabled: bool = True,
        authority_order: Optional[list[str]] = None,
    ) -> tuple[MemoryItem | None, ConflictDecision | None, MemoryItem | None]:
        snippets = self._snippets.setdefault(store_key, [])
        authority_order = authority_order or list(DEFAULT_AUTHORITY_ORDER)
        conflict = None
        deleted = None
        if dedupe_enabled:
            dedup_key = item.meta.get("dedup_key")
            if dedup_key:
                existing_idx = _find_active_idx(snippets, dedup_key)
                if existing_idx is not None:
                    existing = snippets[existing_idx]
                    conflict = resolve_conflict(existing, item, authority_order)
                    if conflict.winner.id == item.id:
                        item = _merge_importance(item, existing)
                        deleted = snippets.pop(existing_idx)
                    else:
                        return existing, conflict, None
        snippets.append(item)
        return item, conflict, deleted

    def apply_retention(self, store_key: str, policy, now_tick: int) -> List[tuple[MemoryItem, str]]:
        snippets = self._snippets.get(store_key, [])
        kept, forgotten = apply_retention(snippets, policy, now_tick=now_tick)
        if kept != snippets:
            self._snippets[store_key] = kept
        return forgotten

    def recall(
        self,
        store_key: str,
        query: str,
        *,
        top_k: int = 3,
        phase_ids: list[str] | None = None,
    ) -> List[MemoryItem]:
        snippets = self._snippets.get(store_key, [])
        phase_rank = None
        if phase_ids is not None:
            phase_set = set(phase_ids)
            snippets = [item for item in snippets if item.meta.get("phase_id") in phase_set]
            phase_rank = {phase_id: idx for idx, phase_id in enumerate(phase_ids)}
        now_tick = max((item.created_at for item in snippets), default=0)
        matches: list[tuple[int, MemoryItem]] = []
        for item in snippets:
            score, reasons = _score_item(item, query, now_tick)
            meta = dict(item.meta)
            meta["score"] = score
            meta["recall_reason"] = reasons
            matches.append((score, replace(item, meta=meta)))
        if phase_rank and len(phase_rank) > 1:
            matches.sort(
                key=lambda pair: (
                    phase_rank.get(pair[1].meta.get("phase_id"), len(phase_rank)),
                    -pair[0],
                    -pair[1].created_at,
                    pair[1].id,
                )
            )
        else:
            matches.sort(key=lambda pair: (-pair[0], -pair[1].created_at, pair[1].id))
        return [item for _, item in matches[:top_k]]

    def all_items(self) -> List[MemoryItem]:
        items: list[MemoryItem] = []
        for entries in self._snippets.values():
            items.extend(entries)
        items.sort(key=lambda item: item.id)
        return items

    def items_for_store(self, store_key: str) -> List[MemoryItem]:
        items = list(self._snippets.get(store_key, []))
        items.sort(key=lambda item: item.id)
        return items

    def delete_item(self, store_key: str, memory_id: str) -> MemoryItem | None:
        items = self._snippets.get(store_key, [])
        for idx, item in enumerate(items):
            if item.id == memory_id:
                return items.pop(idx)
        return None

    def get_item(self, store_key: str, memory_id: str) -> MemoryItem | None:
        items = self._snippets.get(store_key, [])
        for item in items:
            if item.id == memory_id:
                return item
        return None

    def update_item(self, store_key: str, memory_id: str, updater) -> MemoryItem | None:
        items = self._snippets.get(store_key, [])
        for idx, item in enumerate(items):
            if item.id == memory_id:
                updated = updater(item)
                items[idx] = updated
                return updated
        return None

    def has_items(self, store_key: str) -> bool:
        return bool(self._snippets.get(store_key))


def _score_item(item: MemoryItem, query: str, now_tick: int) -> tuple[int, list[str]]:
    reasons: list[str] = []
    sim_score = _similarity_score(query, item.text)
    if sim_score > 0:
        reasons.append("matches_query")
    age = max(now_tick - item.created_at, 0)
    recency_bonus = 2 if age <= 2 else 1 if age <= 5 else 0
    if recency_bonus:
        reasons.append("recency")
    importance_bonus = 2 if item.importance >= 4 else 1 if item.importance >= 2 else 0
    if importance_bonus:
        reasons.append("importance")
    score = sim_score + recency_bonus + importance_bonus
    if not reasons:
        reasons.append("active_rule")
    return score, reasons


def _similarity_score(query: str, text: str) -> int:
    if not query:
        return 0
    q_norm = normalize_text(query)
    t_norm = normalize_text(text)
    if not q_norm or not t_norm:
        return 0
    if q_norm in t_norm:
        return 2
    overlap = set(q_norm.split()) & set(t_norm.split())
    return 1 if overlap else 0


def _find_active_idx(items: List[MemoryItem], dedup_key: str) -> int | None:
    for idx, existing in enumerate(items):
        if existing.meta.get("dedup_key") == dedup_key:
            return idx
    return None


def _merge_importance(incoming: MemoryItem, existing: MemoryItem) -> MemoryItem:
    if existing.importance <= incoming.importance:
        return incoming
    meta = dict(incoming.meta)
    reasons = list(meta.get("importance_reason", []))
    reasons.append("conflict_merge")
    meta["importance_reason"] = reasons
    return replace(incoming, importance=existing.importance, meta=meta)
