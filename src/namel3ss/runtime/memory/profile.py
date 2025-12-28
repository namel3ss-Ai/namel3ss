from __future__ import annotations

from dataclasses import replace
from typing import Dict, List, Optional

from namel3ss.runtime.memory.contract import MemoryItem, MemoryItemFactory, MemoryKind
from namel3ss.runtime.memory_policy.defaults import DEFAULT_AUTHORITY_ORDER
from namel3ss.runtime.memory_policy.evaluation import ConflictDecision, apply_retention, resolve_conflict


class ProfileMemory:
    def __init__(self, *, factory: MemoryItemFactory) -> None:
        self._factory = factory
        self._facts: Dict[str, Dict[str, MemoryItem]] = {}
        self._history: Dict[str, List[MemoryItem]] = {}

    def set_fact(
        self,
        store_key: str,
        key: str,
        value: str,
        *,
        source: str = "user",
        importance: int = 0,
        meta: Optional[dict] = None,
        allow_overwrite: bool = False,
        dedupe_enabled: bool = True,
        authority_order: Optional[list[str]] = None,
    ) -> MemoryItem | None:
        meta_payload = dict(meta or {})
        meta_payload.setdefault("key", key)
        item = self._factory.create(
            session=store_key,
            kind=MemoryKind.PROFILE,
            text=value,
            source=source,
            importance=importance,
            meta=meta_payload,
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
        key = item.meta.get("key")
        if not key:
            return None, None, None
        facts = self._facts.setdefault(store_key, {})
        existing = facts.get(key)
        if existing and dedupe_enabled and existing.text == item.text:
            return None, None, None
        if existing:
            conflict = resolve_conflict(existing, item, authority_order or list(DEFAULT_AUTHORITY_ORDER))
            if conflict.winner.id == item.id:
                facts[key] = item
                return item, conflict, existing
            return existing, conflict, None
        facts[key] = item
        return item, None, None

    def delete_fact(self, store_key: str, key: str) -> bool:
        facts = self._facts.get(store_key, {})
        if key in facts:
            del facts[key]
            return True
        return False

    def replace_fact(
        self,
        store_key: str,
        key: str,
        value: str,
        *,
        source: str = "user",
        importance: int = 0,
        meta: Optional[dict] = None,
    ) -> MemoryItem | None:
        return self.set_fact(
            store_key,
            key,
            value,
            source=source,
            importance=importance,
            meta=meta,
            allow_overwrite=True,
        )

    def recall(self, store_key: str, limit: int = 20, *, phase_ids: list[str] | None = None) -> List[MemoryItem]:
        facts = self._facts.get(store_key, {})
        items = list(facts.values())
        if phase_ids is not None:
            phase_set = set(phase_ids)
            items = [item for item in items if item.meta.get("phase_id") in phase_set]
            if len(phase_ids) > 1:
                phase_rank = {phase_id: idx for idx, phase_id in enumerate(phase_ids)}
                items.sort(
                    key=lambda item: (
                        phase_rank.get(item.meta.get("phase_id"), len(phase_rank)),
                        item.created_at,
                        item.id,
                    )
                )
            else:
                items.sort(key=lambda item: (item.created_at, item.id))
        else:
            items.sort(key=lambda item: (item.created_at, item.id))
        recalled = items[:limit]
        return [_with_recall_reason(item, ["active_rule"]) for item in recalled]

    def all_items(self) -> List[MemoryItem]:
        items: list[MemoryItem] = []
        for facts in self._facts.values():
            items.extend(facts.values())
        items.sort(key=lambda item: item.id)
        return items

    def apply_retention(self, store_key: str, policy, now_tick: int) -> List[tuple[MemoryItem, str]]:
        facts = self._facts.get(store_key, {})
        kept, forgotten = apply_retention(list(facts.values()), policy, now_tick=now_tick)
        kept_ids = {item.id for item in kept}
        for key, item in list(facts.items()):
            if item.id not in kept_ids:
                del facts[key]
        return forgotten

    def delete_item(self, store_key: str, memory_id: str) -> MemoryItem | None:
        facts = self._facts.get(store_key, {})
        for key, item in list(facts.items()):
            if item.id == memory_id:
                del facts[key]
                return item
        return None

    def get_item(self, store_key: str, memory_id: str) -> MemoryItem | None:
        facts = self._facts.get(store_key, {})
        for item in facts.values():
            if item.id == memory_id:
                return item
        return None

    def update_item(self, store_key: str, memory_id: str, updater) -> MemoryItem | None:
        facts = self._facts.get(store_key, {})
        for key, item in list(facts.items()):
            if item.id == memory_id:
                updated = updater(item)
                facts[key] = updated
                return updated
        return None

    def has_items(self, store_key: str) -> bool:
        return bool(self._facts.get(store_key))


def _with_recall_reason(item: MemoryItem, reasons: list[str]) -> MemoryItem:
    meta = dict(item.meta)
    meta["recall_reason"] = reasons
    return replace(item, meta=meta)


__all__ = ["ProfileMemory"]
