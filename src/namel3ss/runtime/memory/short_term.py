from __future__ import annotations

from dataclasses import replace
from typing import Dict, List, Optional

from namel3ss.runtime.memory.contract import MemoryItem, MemoryItemFactory, MemoryKind
from namel3ss.runtime.memory.events import EVENT_CONTEXT, build_dedupe_key
from namel3ss.runtime.memory_lanes.model import ensure_lane_meta
from namel3ss.runtime.memory.importance import importance_for_event
from namel3ss.runtime.memory.summarizer import summarize_items
from namel3ss.runtime.memory_policy.model import AUTHORITY_SYSTEM


class ShortTermMemory:
    def __init__(self, *, factory: MemoryItemFactory) -> None:
        self._factory = factory
        self._messages: Dict[str, Dict[str, List[MemoryItem]]] = {}
        self._summaries: Dict[str, Dict[str, MemoryItem]] = {}

    def record(
        self,
        store_key: str,
        *,
        text: str,
        source: str,
        importance: int = 0,
        meta: Optional[dict] = None,
    ) -> MemoryItem:
        item = self._factory.create(
            session=store_key,
            kind=MemoryKind.SHORT_TERM,
            text=text,
            source=source,
            importance=importance,
            meta=meta or {},
        )
        self.store_item(store_key, item)
        return item

    def store_item(self, store_key: str, item: MemoryItem) -> None:
        phase_id = _phase_id_for(item)
        messages = self._messages.setdefault(store_key, {}).setdefault(phase_id, [])
        messages.append(item)

    def summarize_if_needed(
        self,
        store_key: str,
        max_turns: int,
        *,
        phase_id: str,
        space: str,
        owner: str,
        lane: str,
    ) -> tuple[MemoryItem | None, list[MemoryItem], MemoryItem | None]:
        messages = self._messages.get(store_key, {}).get(phase_id, [])
        if max_turns <= 0 or len(messages) <= max_turns:
            return None, [], None
        evicted = messages[:-max_turns]
        if not evicted:
            return None, [], None
        self._messages.setdefault(store_key, {})[phase_id] = messages[-max_turns:]
        prior = self._summaries.get(store_key, {}).get(phase_id)
        summary_text = summarize_items(evicted, prior_summary=prior.text if prior else None)
        summary_of: list[str] = []
        if prior:
            summary_of.extend(prior.meta.get("summary_of", []))
        summary_of.extend([item.id for item in evicted])
        importance, reasons = importance_for_event(EVENT_CONTEXT, summary_text, "system")
        reasons.append("summary")
        meta = {
            "event_type": EVENT_CONTEXT,
            "summary_of": summary_of,
            "importance_reason": reasons,
            "dedup_key": build_dedupe_key(EVENT_CONTEXT, summary_text),
            "authority": AUTHORITY_SYSTEM,
            "authority_reason": "summary",
            "space": space,
            "owner": owner,
        }
        meta = ensure_lane_meta(meta, lane=lane)
        meta.update(_phase_meta_from_items(evicted, phase_id))
        summary_item = self._factory.create(
            session=store_key,
            kind=MemoryKind.SHORT_TERM,
            text=summary_text,
            source="system",
            importance=importance,
            meta=meta,
        )
        self._summaries.setdefault(store_key, {})[phase_id] = summary_item
        return summary_item, evicted, prior

    def recall(self, store_key: str, limit: int, *, phase_ids: list[str] | None = None) -> List[MemoryItem]:
        if phase_ids is None:
            phases = list(self._messages.get(store_key, {}).keys())
        else:
            phases = phase_ids
        if limit <= 0:
            return []
        items: list[MemoryItem] = []
        for phase_id in phases:
            messages = self._messages.get(store_key, {}).get(phase_id, [])
            summary = self._summaries.get(store_key, {}).get(phase_id)
            if summary:
                items.append(_with_recall_reason(summary, ["active_rule"]))
            for item in messages[-limit:]:
                items.append(_with_recall_reason(item, ["recency"]))
        return items

    def all_items(self) -> List[MemoryItem]:
        items: list[MemoryItem] = []
        for phases in self._messages.values():
            for entries in phases.values():
                items.extend(entries)
        for summaries in self._summaries.values():
            items.extend(summaries.values())
        items.sort(key=lambda item: item.id)
        return items

    def delete_item(self, store_key: str, memory_id: str) -> MemoryItem | None:
        phases = self._messages.get(store_key, {})
        for phase_id, items in phases.items():
            for idx, item in enumerate(items):
                if item.id == memory_id:
                    removed = items.pop(idx)
                    summary = self._summaries.get(store_key, {}).get(phase_id)
                    if summary and summary.id == memory_id:
                        self._summaries.get(store_key, {}).pop(phase_id, None)
                    return removed
        summaries = self._summaries.get(store_key, {})
        for phase_id, summary in list(summaries.items()):
            if summary.id == memory_id:
                summaries.pop(phase_id, None)
                return summary
        return None

    def get_item(self, store_key: str, memory_id: str) -> MemoryItem | None:
        phases = self._messages.get(store_key, {})
        for items in phases.values():
            for item in items:
                if item.id == memory_id:
                    return item
        summaries = self._summaries.get(store_key, {})
        for summary in summaries.values():
            if summary.id == memory_id:
                return summary
        return None

    def update_item(
        self,
        store_key: str,
        memory_id: str,
        updater,
    ) -> MemoryItem | None:
        phases = self._messages.get(store_key, {})
        for phase_id, items in phases.items():
            for idx, item in enumerate(items):
                if item.id == memory_id:
                    updated = updater(item)
                    items[idx] = updated
                    return updated
        summaries = self._summaries.get(store_key, {})
        for phase_id, summary in list(summaries.items()):
            if summary.id == memory_id:
                updated = updater(summary)
                summaries[phase_id] = updated
                return updated
        return None

    def has_items(self, store_key: str) -> bool:
        phases = self._messages.get(store_key, {})
        if any(phases.values()):
            return True
        summaries = self._summaries.get(store_key, {})
        return any(summaries.values())


def _with_recall_reason(item: MemoryItem, reasons: list[str]) -> MemoryItem:
    meta = dict(item.meta)
    meta["recall_reason"] = reasons
    return replace(item, meta=meta)


def _phase_id_for(item: MemoryItem) -> str:
    meta = item.meta or {}
    value = meta.get("phase_id")
    if isinstance(value, str) and value:
        return value
    return "phase-unknown"


def _phase_meta_from_items(items: list[MemoryItem], phase_id: str) -> dict:
    for item in items:
        meta = item.meta or {}
        if meta.get("phase_id") == phase_id:
            payload = {
                "phase_id": phase_id,
                "phase_started_at": meta.get("phase_started_at", 0),
                "phase_reason": meta.get("phase_reason", "auto"),
                "phase_name": meta.get("phase_name"),
            }
            if payload.get("phase_name") is None:
                payload.pop("phase_name", None)
            return payload
    return {
        "phase_id": phase_id,
        "phase_started_at": 0,
        "phase_reason": "auto",
    }
