from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from namel3ss.config.model import AppConfig
from namel3ss.ir import nodes as ir
from namel3ss.runtime.ai.provider import AIProvider
from namel3ss.runtime.ai.trace import AITrace
from namel3ss.runtime.memory.manager import MemoryManager
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.schema.records import RecordSchema


@dataclass
class ExecutionContext:
    flow: ir.Flow
    schemas: Dict[str, RecordSchema]
    state: Dict[str, object]
    locals: Dict[str, object]
    constants: set[str]
    last_value: Optional[object]
    store: MemoryStore
    ai_provider: AIProvider
    ai_profiles: Dict[str, ir.AIDecl]
    agents: Dict[str, ir.AgentDecl]
    traces: list[AITrace]
    memory_manager: MemoryManager
    agent_calls: int
    config: AppConfig
    provider_cache: Dict[str, AIProvider]
