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
from namel3ss.observability.context import ObservabilityContext


@dataclass
class CallFrame:
    function_name: str
    locals: Dict[str, object]
    return_target: str | None


class TraceEvent(dict):
    __slots__ = ()

    def __getattr__(self, name: str) -> object:
        if name in self:
            return self[name]
        raise AttributeError(name)


class TraceList(list):
    def __init__(self, items: list[object] | None = None) -> None:
        super().__init__([_wrap_trace(item) for item in (items or [])])

    def append(self, item: object) -> None:
        super().append(_wrap_trace(item))

    def extend(self, items) -> None:
        super().extend(_wrap_trace(item) for item in items)


def _wrap_trace(item: object) -> object:
    if isinstance(item, dict) and not isinstance(item, TraceEvent):
        return TraceEvent(item)
    return item


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
    capabilities: tuple[str, ...]
    pack_allowlist: tuple[str, ...] | None
    jobs: Dict[str, ir.JobDecl]
    job_order: list[str]
    traces: list[AITrace]
    memory_manager: MemoryManager
    agent_calls: int
    config: AppConfig
    provider_cache: Dict[str, AIProvider]
    runtime_theme: str | None
    sensitive: bool = False
    sensitive_config: object | None = None
    encryption_service: object | None = None
    model_manager: object | None = None
    sandbox_config: object | None = None
    last_order_target: ir.Assignable | None = None
    flow_map: Dict[str, ir.Flow] = field(default_factory=dict)
    flow_contracts: Dict[str, ir.ContractDecl] = field(default_factory=dict)
    pipeline_contracts: Dict[str, ir.ContractDecl] = field(default_factory=dict)
    policy: ir.PolicyDecl | None = None
    auth_context: object | None = None
    project_root: str | None = None
    app_path: str | None = None
    observability: ObservabilityContext | None = None
    record_changes: list[dict] = field(default_factory=list)
    execution_steps: list[dict] = field(default_factory=list)
    execution_step_counter: int = 0
    pending_tool_traces: list[dict] = field(default_factory=list)
    tool_call_source: str | None = None
    call_stack: list[CallFrame] = field(default_factory=list)
    flow_stack: list[str] = field(default_factory=list)
    parallel_mode: bool = False
    parallel_task: str | None = None
    last_ai_provider: str | None = None
    calc_assignment_index: dict[int, dict[str, int]] = field(default_factory=dict)
    flow_action_id: str | None = None
    flow_call_id: str | None = None
    flow_call_counter: int = 0
    orchestration_counter: int = 0
    job_queue: list[dict] = field(default_factory=list)
    job_trigger_state: dict[str, bool] = field(default_factory=dict)
    scheduled_jobs: list[dict] = field(default_factory=list)
    job_enqueue_counter: int = 0
    logical_time: int = 0
    async_tasks: dict[str, object] = field(default_factory=dict)
    async_launch_counter: int = 0
    yield_messages: list[dict] = field(default_factory=list)
    yield_sequence: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.traces, TraceList):
            self.traces = TraceList(list(self.traces or []))
