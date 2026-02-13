from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from namel3ss.config.model import AppConfig
from namel3ss.runtime.memory.api import MemoryManager
from namel3ss.runtime.storage.base import Storage
from namel3ss.runtime.ui.contracts.program_contract import ProgramContract


@dataclass(frozen=True, slots=True)
class ActionDispatchContext:
    program_ir: ProgramContract
    action: dict
    action_id: str
    action_type: str
    payload: dict
    state: dict
    store: Storage
    runtime_theme: Optional[str]
    config: AppConfig
    manifest: dict
    identity: dict | None
    auth_context: object | None
    session: dict | None
    source: str | None
    secret_values: list[str]
    memory_manager: MemoryManager | None
    preference_store: object | None
    preference_key: str | None
    allow_theme_override: bool | None
    raise_on_error: bool
    ui_mode: str
    diagnostics_enabled: bool


__all__ = ["ActionDispatchContext"]
