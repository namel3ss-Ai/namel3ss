from __future__ import annotations

from dataclasses import dataclass, field

from namel3ss.runtime.store.memory_store import MemoryStore


@dataclass
class SessionState:
    state: dict = field(default_factory=dict)
    store: MemoryStore = field(default_factory=MemoryStore)
