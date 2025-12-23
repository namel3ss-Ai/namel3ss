from __future__ import annotations

import copy
from typing import Dict, Optional

from namel3ss.config.loader import load_config
from namel3ss.config.model import AppConfig
from namel3ss.ir import nodes as ir
from namel3ss.runtime.ai.mock_provider import MockProvider
from namel3ss.runtime.ai.provider import AIProvider
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.identity.context import resolve_identity
from namel3ss.runtime.identity.guards import enforce_requires
from namel3ss.runtime.audit.recorder import record_audit_entry
from namel3ss.runtime.executor.result import ExecutionResult
from namel3ss.runtime.executor.signals import _ReturnSignal
from namel3ss.runtime.executor.statements import execute_statement
from namel3ss.runtime.memory.manager import MemoryManager
from namel3ss.runtime.storage.factory import resolve_store
from namel3ss.schema.identity import IdentitySchema
from namel3ss.schema.records import RecordSchema
from namel3ss.secrets import collect_secret_values


class Executor:
    def __init__(
        self,
        flow: ir.Flow,
        schemas: Optional[Dict[str, RecordSchema]] = None,
        initial_state: Optional[Dict[str, object]] = None,
        store: Optional[object] = None,
        input_data: Optional[Dict[str, object]] = None,
        ai_provider: Optional[AIProvider] = None,
        ai_profiles: Optional[Dict[str, ir.AIDecl]] = None,
        memory_manager: Optional[MemoryManager] = None,
        agents: Optional[Dict[str, ir.AgentDecl]] = None,
        config: Optional[AppConfig] = None,
        runtime_theme: Optional[str] = None,
        identity_schema: IdentitySchema | None = None,
        identity: dict | None = None,
        project_root: str | None = None,
    ) -> None:
        resolved_config = config or load_config()
        default_ai_provider = ai_provider or MockProvider()
        provider_cache = {"mock": default_ai_provider}
        resolved_store = resolve_store(store, config=resolved_config)
        starting_state = initial_state if initial_state is not None else resolved_store.load_state()
        resolved_identity = identity if identity is not None else resolve_identity(resolved_config, identity_schema)
        self.ctx = ExecutionContext(
            flow=flow,
            schemas=schemas or {},
            state=starting_state or {},
            locals={"input": input_data or {}},
            identity=resolved_identity,
            constants=set(),
            last_value=None,
            store=resolved_store,
            ai_provider=default_ai_provider,
            ai_profiles=ai_profiles or {},
            agents=agents or {},
            traces=[],
            memory_manager=memory_manager or MemoryManager(),
            agent_calls=0,
            config=resolved_config,
            provider_cache=provider_cache,
            runtime_theme=runtime_theme,
            project_root=project_root,
            record_changes=[],
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
        enforce_requires(
            self.ctx,
            getattr(self.ctx.flow, "requires", None),
            subject=f'flow "{self.ctx.flow.name}"',
            line=self.ctx.flow.line,
            column=self.ctx.flow.column,
        )
        audit_before = None
        if getattr(self.ctx.flow, "audited", False):
            audit_before = copy.deepcopy(self.ctx.state)
        self.ctx.store.begin()
        try:
            try:
                for stmt in self.ctx.flow.body:
                    execute_statement(self.ctx, stmt)
            except _ReturnSignal as signal:
                self.ctx.last_value = signal.value
            if audit_before is not None:
                secret_values = collect_secret_values(self.ctx.config)
                record_audit_entry(
                    self.ctx.store,
                    flow_name=self.ctx.flow.name,
                    identity=self.ctx.identity,
                    before=audit_before,
                    after=self.ctx.state,
                    record_changes=self.ctx.record_changes,
                    project_root=self.ctx.project_root,
                    secret_values=secret_values,
                )
            self.ctx.store.save_state(self.ctx.state)
            self.ctx.store.commit()
        except Exception:
            try:
                self.ctx.store.rollback()
            except Exception:
                pass
            raise
        self.last_value = self.ctx.last_value
        self.agent_calls = self.ctx.agent_calls
        return ExecutionResult(
            state=self.ctx.state,
            last_value=self.ctx.last_value,
            traces=self.ctx.traces,
            runtime_theme=self.ctx.runtime_theme,
        )
