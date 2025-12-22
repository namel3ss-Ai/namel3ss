from __future__ import annotations

from dataclasses import dataclass, field

from namel3ss.runtime.storage.base import Storage
from namel3ss.runtime.storage.factory import create_store


@dataclass
class SessionState:
    state: dict = field(default_factory=dict)
    store: Storage = field(default_factory=create_store)
    runtime_theme: str | None = None
