from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Any, Dict, Iterable, Tuple

from namel3ss.errors.base import Namel3ssError

MEMORY_SCOPE_SESSION = "session"
MEMORY_SCOPES = {MEMORY_SCOPE_SESSION}


class MemoryKind(str, Enum):
    SHORT_TERM = "short_term"
    SEMANTIC = "semantic"
    PROFILE = "profile"


@dataclass(frozen=True)
class MemoryItem:
    id: str
    kind: MemoryKind
    text: str
    source: str
    created_at: int
    importance: int = 0
    scope: str = MEMORY_SCOPE_SESSION
    meta: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "text": self.text,
            "source": self.source,
            "created_at": self.created_at,
            "importance": self.importance,
            "scope": self.scope,
            "meta": dict(self.meta) if self.meta else {},
        }


class MemoryClock:
    def __init__(self, start: int = 1) -> None:
        self._tick = start - 1

    def now(self) -> int:
        self._tick += 1
        return self._tick

    def current(self) -> int:
        return self._tick


class MemoryIdGenerator:
    def __init__(self) -> None:
        self._counters: Dict[Tuple[str, MemoryKind], int] = {}

    def next_id(self, session: str, kind: MemoryKind) -> str:
        key = (session, kind)
        self._counters[key] = self._counters.get(key, 0) + 1
        return f"{session}:{kind.value}:{self._counters[key]}"


class MemoryItemFactory:
    def __init__(self, *, clock: MemoryClock, id_generator: MemoryIdGenerator) -> None:
        self._clock = clock
        self._ids = id_generator

    def create(
        self,
        *,
        session: str,
        kind: MemoryKind,
        text: str,
        source: str,
        importance: int = 0,
        scope: str = MEMORY_SCOPE_SESSION,
        meta: Dict[str, Any] | None = None,
    ) -> MemoryItem:
        item = MemoryItem(
            id=self._ids.next_id(session, kind),
            kind=kind,
            text=text,
            source=source,
            created_at=self._clock.now(),
            importance=importance,
            scope=scope,
            meta=meta or {},
        )
        return item


def _coerce_kind(kind: MemoryKind | str) -> MemoryKind:
    if isinstance(kind, MemoryKind):
        return kind
    if isinstance(kind, str):
        normalized = kind.strip().lower()
        for entry in MemoryKind:
            if entry.value == normalized:
                return entry
    raise Namel3ssError(
        "Invalid memory kind. Expected one of: short_term, semantic, profile.",
        details={"kind": kind},
    )


def validate_memory_kind(kind: MemoryKind | str) -> MemoryKind:
    return _coerce_kind(kind)


def validate_scope(scope: str) -> str:
    if scope not in MEMORY_SCOPES:
        raise Namel3ssError(
            "Invalid memory scope. Phase 0 supports only 'session'.",
            details={"scope": scope},
        )
    return scope


def normalize_memory_item(item: MemoryItem | dict) -> dict:
    if isinstance(item, MemoryItem):
        return item.as_dict()
    data = dict(item)
    kind = data.get("kind")
    if isinstance(kind, MemoryKind):
        data["kind"] = kind.value
    if data.get("meta") is None:
        data["meta"] = {}
    return data


def validate_memory_item(item: MemoryItem | dict) -> None:
    data = normalize_memory_item(item)
    required = ("id", "kind", "text", "source", "created_at", "importance", "scope", "meta")
    missing = [key for key in required if key not in data]
    if missing:
        raise Namel3ssError(
            f"Memory item missing required fields: {', '.join(missing)}.",
            details={"required": required},
        )
    if not isinstance(data["id"], str) or not data["id"]:
        raise Namel3ssError("Memory item id must be a non-empty string.")
    _coerce_kind(data["kind"])
    if not isinstance(data["text"], str):
        raise Namel3ssError("Memory item text must be a string.")
    if not isinstance(data["source"], str) or not data["source"]:
        raise Namel3ssError("Memory item source must be a non-empty string.")
    created_at = data["created_at"]
    if not isinstance(created_at, int) or isinstance(created_at, bool) or created_at < 0:
        raise Namel3ssError(
            "Memory item created_at must be a deterministic integer counter.",
            details={"created_at": created_at},
        )
    importance = data["importance"]
    if not isinstance(importance, (int, float)) or isinstance(importance, bool):
        raise Namel3ssError("Memory item importance must be a number.")
    validate_scope(data["scope"])
    if not isinstance(data["meta"], dict):
        raise Namel3ssError("Memory item meta must be a dict.")


def deterministic_recall_hash(items: Iterable[MemoryItem | dict]) -> str:
    pairs = []
    for item in items:
        data = normalize_memory_item(item)
        pairs.append(f"{data['kind']}:{data['id']}")
    payload = "|".join(pairs).encode("utf-8")
    return sha256(payload).hexdigest()


__all__ = [
    "MEMORY_SCOPE_SESSION",
    "MemoryClock",
    "MemoryIdGenerator",
    "MemoryItem",
    "MemoryItemFactory",
    "MemoryKind",
    "deterministic_recall_hash",
    "normalize_memory_item",
    "validate_memory_item",
    "validate_memory_kind",
    "validate_scope",
]
