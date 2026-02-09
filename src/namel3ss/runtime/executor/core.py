from __future__ import annotations

import copy
from pathlib import Path
from typing import Dict, Optional

from namel3ss.config.loader import load_config
from namel3ss.config.model import AppConfig
from namel3ss.ir import nodes as ir
from namel3ss.runtime.ai.mock_provider import MockProvider
from namel3ss.runtime.ai.provider import AIProvider
from namel3ss.runtime.ai.model_manager import load_model_manager
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.executor.records import _persist_execution_artifacts, _write_run_outcome, _write_tools_with_pack
from namel3ss.runtime.executor.result import ExecutionResult
from namel3ss.runtime.executor.signals import _ReturnSignal
from namel3ss.runtime.executor.statements import execute_statement
from namel3ss.runtime.executor.traces import _dict_traces, _record_error_step, _record_flow_end
from namel3ss.runtime.execution.calc_index import build_calc_assignment_index
from namel3ss.runtime.execution.recorder import record_step
from namel3ss.runtime.flow.runner import run_declarative_flow
from namel3ss.runtime.identity.context import resolve_identity
from namel3ss.runtime.identity.guards import enforce_requires
from namel3ss.runtime.backend.job_queue import initialize_job_triggers, run_job_queue, update_job_triggers
from namel3ss.runtime.memory.api import MemoryManager
from namel3ss.runtime.mutation_policy import requires_mentions_mutation
from namel3ss.runtime.storage.factory import resolve_store
from namel3ss.schema.evolution import enforce_runtime_schema_compatibility
from namel3ss.schema.identity import IdentitySchema
from namel3ss.schema.records import RecordSchema
from namel3ss.secrets import collect_secret_values, discover_required_secrets_for_profiles
from namel3ss.secrets.context import get_engine_target
from namel3ss.runtime.audit.recorder import record_audit_entry
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.runtime.api import build_runtime_error
from namel3ss.errors.runtime.model import RuntimeWhere
from namel3ss.runtime.boundary import attach_project_root, attach_secret_values, boundary_from_error, mark_boundary
from namel3ss.security import activate_security_wall, build_security_wall
from namel3ss.runtime.security import load_sensitive_config
from namel3ss.runtime.sandbox.config import load_sandbox_config
from namel3ss.runtime.sandbox.runner import run_sandbox_flow
from namel3ss.runtime.security.resource_limits import load_resource_limits
from namel3ss.security_encryption import load_encryption_service
from namel3ss.observability.context import ObservabilityContext
from namel3ss.observability.enablement import resolve_observability_context
from namel3ss.purity import is_pure
from namel3ss.runtime.performance.state import build_or_get_performance_state


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
        tools: Optional[Dict[str, ir.ToolDecl]] = None,
        functions: Optional[Dict[str, ir.FunctionDecl]] = None,
        flows: Optional[Dict[str, ir.Flow]] = None,
        flow_contracts: Optional[Dict[str, ir.ContractDecl]] = None,
        pipeline_contracts: Optional[Dict[str, ir.ContractDecl]] = None,
        jobs: Optional[Dict[str, ir.JobDecl]] = None,
        capabilities: tuple[str, ...] | None = None,
        pack_allowlist: tuple[str, ...] | None = None,
        job_order: list[str] | None = None,
        config: Optional[AppConfig] = None,
        runtime_theme: Optional[str] = None,
        identity_schema: IdentitySchema | None = None,
        identity: dict | None = None,
        auth_context: object | None = None,
        session: dict | None = None,
        project_root: str | None = None,
        app_path: str | None = None,
        flow_action_id: str | None = None,
        policy: ir.PolicyDecl | None = None,
        observability: ObservabilityContext | None = None,
        extension_hook_manager: object | None = None,
        app_permissions: dict[str, bool] | None = None,
        app_permissions_enabled: bool = False,
        ui_state_scope_by_key: dict[str, str] | None = None,
    ) -> None:
        resolved_config = config or load_config()
        default_ai_provider = ai_provider or MockProvider()
        provider_cache = {"mock": default_ai_provider}
        resolved_store = resolve_store(store, config=resolved_config)
        enforce_runtime_schema_compatibility(
            (schemas or {}).values(),
            project_root=project_root,
            store=resolved_store,
        )
        self._state_loaded_from_store = initial_state is None
        starting_state = initial_state if initial_state is not None else resolved_store.load_state()
        resolved_identity = identity if identity is not None else resolve_identity(resolved_config, identity_schema)
        ai_profiles = ai_profiles or {}
        secrets_map = _build_secrets_map(ai_profiles, resolved_config, app_path)
        obs, _ = resolve_observability_context(
            observability,
            project_root=project_root,
            app_path=app_path,
            config=resolved_config,
        )
        sensitive_config = load_sensitive_config(project_root, app_path)
        sensitive = sensitive_config.is_sensitive(flow.name)
        encryption_service = load_encryption_service(project_root, app_path, required=sensitive)
        model_manager = load_model_manager(project_root, app_path)
        sandbox_config = load_sandbox_config(project_root, app_path)
        resource_limits = load_resource_limits(
            project_root=project_root,
            app_path=app_path,
            capabilities=tuple(capabilities or ()),
        )
        locals_payload = {"input": input_data or {}, "secrets": secrets_map}
        if isinstance(session, dict):
            locals_payload["session"] = dict(session)
        self.ctx = ExecutionContext(
            flow=flow,
            schemas=schemas or {},
            state=starting_state or {},
            locals=locals_payload,
            identity=resolved_identity,
            auth_context=auth_context,
            constants=set(),
            last_value=None,
            store=resolved_store,
            ai_provider=default_ai_provider,
            ai_profiles=ai_profiles,
            agents=agents or {},
            tools=tools or {},
            functions=functions or {},
            flow_map=flows or {flow.name: flow},
            flow_contracts=flow_contracts or {},
            pipeline_contracts=pipeline_contracts or {},
            capabilities=tuple(capabilities or ()),
            pack_allowlist=pack_allowlist,
            jobs=jobs or {},
            job_order=list(job_order or list((jobs or {}).keys())),
            traces=[],
            memory_manager=memory_manager or MemoryManager(project_root=project_root, app_path=app_path),
            agent_calls=0,
            config=resolved_config,
            policy=policy,
            provider_cache=provider_cache,
            runtime_theme=runtime_theme,
            project_root=project_root,
            app_path=app_path,
            observability=obs,
            record_changes=[],
            execution_steps=[],
            execution_step_counter=0,
            flow_action_id=flow_action_id,
            extension_hook_manager=extension_hook_manager,
            sensitive=sensitive,
            sensitive_config=sensitive_config,
            encryption_service=encryption_service,
            model_manager=model_manager,
            sandbox_config=sandbox_config,
            resource_limits=resource_limits,
            app_permissions=dict(app_permissions or {}),
            app_permissions_enabled=bool(app_permissions_enabled),
            ui_state_scope_by_key=dict(ui_state_scope_by_key or {}),
        )
        self.ctx.performance_state = build_or_get_performance_state(
            config=resolved_config,
            capabilities=tuple(capabilities or ()),
            project_root=project_root,
            app_path=app_path,
        )
        self.ctx.calc_assignment_index = _load_calc_assignment_index(app_path)
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
        self.tools = self.ctx.tools
        self.traces = self.ctx.traces
        self.memory_manager = self.ctx.memory_manager
        self.agent_calls = self.ctx.agent_calls
        self.config = self.ctx.config
        self.provider_cache = self.ctx.provider_cache
        self.extension_hook_manager = self.ctx.extension_hook_manager

    def run(self) -> ExecutionResult:
        wall = build_security_wall(self.ctx.config, self.ctx.traces)
        with activate_security_wall(wall):
            return self._run_internal()

    def _run_internal(self) -> ExecutionResult:
        purity = getattr(self.ctx.flow, "purity", None)
        record_step(
            self.ctx,
            kind="flow_start",
            what=f'flow "{self.ctx.flow.name}" started',
            data={"purity": purity} if is_pure(purity) else None,
            line=self.ctx.flow.line,
            column=self.ctx.flow.column,
        )
        initialize_job_triggers(self.ctx)
        error: Exception | None = None
        store_started = False
        store_began = False
        store_committed = False
        store_commit_failed = False
        store_rolled_back = False
        store_rollback_failed = False
        state_save_attempted = False
        state_save_succeeded = False
        state_save_failed = False
        memory_persist_attempted = False
        memory_persist_succeeded = False
        memory_persist_failed = False
        self.ctx.current_statement = None
        self.ctx.current_statement_index = None
        try:
            requires_expr = getattr(self.ctx.flow, "requires", None)
            if not requires_mentions_mutation(requires_expr):
                enforce_requires(
                    self.ctx,
                    requires_expr,
                    subject=f'flow "{self.ctx.flow.name}"',
                    line=self.ctx.flow.line,
                    column=self.ctx.flow.column,
                )
            audit_before = None
            if getattr(self.ctx.flow, "audited", False):
                audit_before = copy.deepcopy(self.ctx.state)
            try:
                self.ctx.store.begin()
                store_began = True
            except Exception as err:
                mark_boundary(err, "store", action="begin")
                raise
            store_started = True
            try:
                sandbox_flow = None
                if self.ctx.sandbox_config:
                    sandbox_flow = self.ctx.sandbox_config.flow_for(self.ctx.flow.name)
                if sandbox_flow is not None:
                    inputs = dict(self.ctx.locals.get("input") or {})
                    payload = {
                        "inputs": inputs,
                        "input": inputs,
                        "state": dict(self.ctx.state or {}),
                        "identity": dict(self.ctx.identity or {}),
                    }
                    sandbox_result = run_sandbox_flow(
                        project_root=self.ctx.project_root,
                        app_path=self.ctx.app_path,
                        flow_name=self.ctx.flow.name,
                        payload=payload,
                    )
                    if not sandbox_result.get("ok"):
                        error = sandbox_result.get("error") or {}
                        raise Namel3ssError(
                            error.get("message") or "Sandbox execution failed.",
                            line=self.ctx.flow.line,
                            column=self.ctx.flow.column,
                        )
                    self.ctx.last_value = sandbox_result.get("result")
                elif getattr(self.ctx.flow, "declarative", False):
                    run_declarative_flow(self.ctx)
                elif getattr(self.ctx.flow, "ai_metadata", None) is not None and not getattr(self.ctx.flow, "body", None):
                    from namel3ss.runtime.executor.ai_patterns import execute_ai_metadata_flow

                    execute_ai_metadata_flow(self.ctx)
                else:
                    for idx, stmt in enumerate(self.ctx.flow.body, start=1):
                        self.ctx.current_statement = stmt
                        self.ctx.current_statement_index = idx
                        execute_statement(self.ctx, stmt)
            except _ReturnSignal as signal:
                self.ctx.last_value = signal.value
            update_job_triggers(self.ctx)
            run_job_queue(self.ctx)
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
            try:
                state_save_attempted = True
                self.ctx.store.save_state(self.ctx.state)
                state_save_succeeded = True
            except Exception as err:
                state_save_failed = True
                mark_boundary(err, "store", action="save_state")
                raise
            try:
                self.ctx.store.commit()
                store_committed = True
            except Exception as err:
                store_commit_failed = True
                mark_boundary(err, "store", action="commit")
                raise
            secret_values = collect_secret_values(self.ctx.config)
            try:
                memory_persist_attempted = True
                self.ctx.memory_manager.persist(
                    project_root=self.ctx.project_root,
                    app_path=self.ctx.app_path,
                    secret_values=secret_values,
                )
                memory_persist_succeeded = True
            except Exception as err:
                memory_persist_failed = True
                mark_boundary(err, "memory", action="persist")
                raise
        except Exception as exc:
            error = exc
            _record_error_step(self.ctx, exc)
            if store_started:
                try:
                    self.ctx.store.rollback()
                    store_rolled_back = True
                except Exception:
                    store_rollback_failed = True
                    pass
            attach_project_root(exc, self.ctx.project_root)
            attach_secret_values(exc, collect_secret_values(self.ctx.config))
            boundary = boundary_from_error(exc) or "engine"
            where = _build_runtime_where(self.ctx, exc)
            pack, message, _ = build_runtime_error(boundary=boundary, err=exc, where=where, traces=_dict_traces(self.ctx.traces))
            self.ctx.traces.append(
                {
                    "type": "runtime_error",
                    "error_id": pack.error.error_id,
                    "boundary": pack.error.boundary,
                    "kind": pack.error.kind,
                }
            )
            details = {"error_id": pack.error.error_id}
            if isinstance(exc, Namel3ssError) and isinstance(exc.details, dict):
                for key in ("category", "reason_code"):
                    if key in exc.details:
                        details[key] = exc.details[key]
                if exc.details.get("error_id"):
                    details["cause"] = exc.details
            raise Namel3ssError(
                message,
                line=where.line,
                column=where.column,
                details=details,
            ) from exc
        finally:
            from namel3ss.runtime.executor.ai_runner import _flush_pending_tool_traces

            _flush_pending_tool_traces(self.ctx)
            _record_flow_end(self.ctx, ok=error is None)
            _persist_execution_artifacts(self.ctx, ok=error is None, error=error)
            _write_tools_with_pack(self.ctx)
            _write_run_outcome(
                self.ctx,
                store_began=store_began,
                store_committed=store_committed,
                store_commit_failed=store_commit_failed,
                store_rolled_back=store_rolled_back,
                store_rollback_failed=store_rollback_failed,
                state_save_attempted=state_save_attempted,
                state_save_succeeded=state_save_succeeded,
                state_save_failed=state_save_failed,
                memory_persist_attempted=memory_persist_attempted,
                memory_persist_succeeded=memory_persist_succeeded,
                memory_persist_failed=memory_persist_failed,
                error_escaped=error is not None,
                state_loaded_from_store=self._state_loaded_from_store,
            )
        self.last_value = self.ctx.last_value
        self.agent_calls = self.ctx.agent_calls
        return ExecutionResult(
            state=self.ctx.state,
            last_value=self.ctx.last_value,
            traces=self.ctx.traces,
            execution_steps=list(self.ctx.execution_steps or []),
            yield_messages=list(self.ctx.yield_messages or []),
            runtime_theme=self.ctx.runtime_theme,
        )


def _build_runtime_where(ctx: ExecutionContext, error: Exception) -> RuntimeWhere:
    stmt = getattr(ctx, "current_statement", None)
    idx = getattr(ctx, "current_statement_index", None)
    stmt_kind = _statement_kind(stmt)
    line = getattr(error, "line", None)
    column = getattr(error, "column", None)
    if line is None and stmt is not None:
        line = getattr(stmt, "line", None)
        column = getattr(stmt, "column", None)
    return RuntimeWhere(
        flow_name=getattr(ctx.flow, "name", None),
        statement_kind=stmt_kind,
        statement_index=idx,
        line=line,
        column=column,
    )


def _statement_kind(stmt: object) -> str | None:
    if stmt is None:
        return None
    if isinstance(stmt, ir.AskAIStmt):
        return "ask_ai"
    if isinstance(stmt, ir.Save):
        return "save"
    if isinstance(stmt, ir.Create):
        return "create"
    if isinstance(stmt, ir.Find):
        return "find"
    if isinstance(stmt, ir.Update):
        return "update"
    if isinstance(stmt, ir.Delete):
        return "delete"
    if isinstance(stmt, ir.If):
        return "if"
    if isinstance(stmt, ir.Match):
        return "match"
    if isinstance(stmt, ir.TryCatch):
        return "try"
    if isinstance(stmt, ir.Repeat):
        return "repeat"
    if isinstance(stmt, ir.ForEach):
        return "for_each"
    if isinstance(stmt, ir.Set):
        return "set"
    if isinstance(stmt, ir.Let):
        return "let"
    if isinstance(stmt, ir.Return):
        return "return"
    if isinstance(stmt, ir.AwaitStmt):
        return "await"
    if isinstance(stmt, ir.YieldStmt):
        return "yield"
    if isinstance(stmt, ir.ThemeChange):
        return "theme"
    if isinstance(stmt, ir.LogStmt):
        return "log"
    if isinstance(stmt, ir.MetricStmt):
        return "metric"
    if isinstance(stmt, ir.EnqueueJob):
        return "enqueue_job"
    if isinstance(stmt, ir.AdvanceTime):
        return "tick"
    if isinstance(stmt, ir.RunAgentStmt):
        return "run_agent"
    if isinstance(stmt, ir.RunAgentsParallelStmt):
        return "run_agents_parallel"
    if isinstance(stmt, ir.ParallelBlock):
        return "parallel"
    if isinstance(stmt, ir.OrchestrationBlock):
        return "orchestration"
    return None


def _build_secrets_map(ai_profiles: dict, config: AppConfig, app_path: str | None) -> dict[str, dict[str, object]]:
    path_value = None
    if app_path:
        path_value = Path(app_path) if not isinstance(app_path, Path) else app_path
    target = get_engine_target()
    refs = discover_required_secrets_for_profiles(ai_profiles, config, target=target, app_path=path_value)
    return {
        ref.name: {"name": ref.name, "available": ref.available, "source": ref.source, "target": ref.target}
        for ref in refs
    }


def _load_calc_assignment_index(app_path: str | Path | None) -> dict[int, dict[str, int]]:
    if not app_path:
        return {}
    path = Path(app_path)
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    return build_calc_assignment_index(source)


__all__ = ["Executor"]
