from __future__ import annotations

from dataclasses import dataclass, field

from namel3ss.config.model import AppConfig
from namel3ss.runtime.storage.base import Storage
from namel3ss.runtime.storage.factory import create_store
from namel3ss.runtime.memory.api import MemoryManager


@dataclass
class SessionState:
    state: dict = field(default_factory=dict)
    store: Storage | None = None
    runtime_theme: str | None = None
    memory_manager: MemoryManager | None = None

    def ensure_store(self, config: AppConfig | None = None) -> Storage:
        if self.store is None:
            self.store = create_store(config=config)
        return self.store
