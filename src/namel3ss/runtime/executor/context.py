from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from namel3ss.config.model import AppConfig
from namel3ss.ir import nodes as ir
from namel3ss.runtime.ai.provider import AIProvider
from namel3ss.runtime.ai.trace import AITrace
from namel3ss.runtime.memory.api import MemoryManager
from namel3ss.runtime.storage.base import Storage
from namel3ss.schema.records import RecordSchema


@dataclass
class CallFrame:
    function_name: str
    locals: Dict[str, object]
    return_target: str | None


@dataclass
class ExecutionContext:
    flow: ir.Flow
    schemas: Dict[str, RecordSchema]
    state: Dict[str, object]
    locals: Dict[str, object]
    identity: Dict[str, object]
    constants: set[str]
    last_value: Optional[object]
    store: Storage
    ai_provider: AIProvider
    ai_profiles: Dict[str, ir.AIDecl]
    agents: Dict[str, ir.AgentDecl]
    tools: Dict[str, ir.ToolDecl]
    functions: Dict[str, ir.FunctionDecl]
    traces: list[AITrace]
    memory_manager: MemoryManager
    agent_calls: int
    config: AppConfig
    provider_cache: Dict[str, AIProvider]
    runtime_theme: str | None
    project_root: str | None = None
    app_path: str | None = None
    record_changes: list[dict] = field(default_factory=list)
    execution_steps: list[dict] = field(default_factory=list)
    execution_step_counter: int = 0
    pending_tool_traces: list[dict] = field(default_factory=list)
    tool_call_source: str | None = None
    call_stack: list[CallFrame] = field(default_factory=list)
    parallel_mode: bool = False
    parallel_task: str | None = None
    last_ai_provider: str | None = None
    calc_assignment_index: dict[int, dict[str, int]] = field(default_factory=dict)
