from __future__ import annotations

from typing import Dict, Optional

from namel3ss.config.loader import load_config
from namel3ss.config.model import AppConfig
from namel3ss.ir import nodes as ir
from namel3ss.runtime.ai.mock_provider import MockProvider
from namel3ss.runtime.ai.provider import AIProvider
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.executor.result import ExecutionResult
from namel3ss.runtime.executor.signals import _ReturnSignal
from namel3ss.runtime.executor.statements import execute_statement
from namel3ss.runtime.memory.manager import MemoryManager
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.schema.records import RecordSchema


class Executor:
    def __init__(
        self,
        flow: ir.Flow,
        schemas: Optional[Dict[str, RecordSchema]] = None,
        initial_state: Optional[Dict[str, object]] = None,
        store: Optional[MemoryStore] = None,
        input_data: Optional[Dict[str, object]] = None,
        ai_provider: Optional[AIProvider] = None,
        ai_profiles: Optional[Dict[str, ir.AIDecl]] = None,
        memory_manager: Optional[MemoryManager] = None,
        agents: Optional[Dict[str, ir.AgentDecl]] = None,
        config: Optional[AppConfig] = None,
    ) -> None:
        resolved_config = config or load_config()
        default_ai_provider = ai_provider or MockProvider()
        provider_cache = {"mock": default_ai_provider}
        self.ctx = ExecutionContext(
            flow=flow,
            schemas=schemas or {},
            state=initial_state or {},
            locals={"input": input_data or {}},
            constants=set(),
            last_value=None,
            store=store or MemoryStore(),
            ai_provider=default_ai_provider,
            ai_profiles=ai_profiles or {},
            agents=agents or {},
            traces=[],
            memory_manager=memory_manager or MemoryManager(),
            agent_calls=0,
            config=resolved_config,
            provider_cache=provider_cache,
        )
        self.flow = self.ctx.flow
        self.schemas = self.ctx.schemas
        self.state = self.ctx.state
        self.locals = self.ctx.locals
        self.constants = self.ctx.constants
        self.last_value = self.ctx.last_value
        self.store = self.ctx.store
        self.ai_provider = self.ctx.ai_provider
        self.ai_profiles = self.ctx.ai_profiles
        self.agents = self.ctx.agents
        self.traces = self.ctx.traces
        self.memory_manager = self.ctx.memory_manager
        self.agent_calls = self.ctx.agent_calls
        self.config = self.ctx.config
        self.provider_cache = self.ctx.provider_cache

    def run(self) -> ExecutionResult:
        try:
            for stmt in self.ctx.flow.body:
                execute_statement(self.ctx, stmt)
        except _ReturnSignal as signal:
            self.ctx.last_value = signal.value
        self.last_value = self.ctx.last_value
        self.agent_calls = self.ctx.agent_calls
        return ExecutionResult(state=self.ctx.state, last_value=self.ctx.last_value, traces=self.ctx.traces)
