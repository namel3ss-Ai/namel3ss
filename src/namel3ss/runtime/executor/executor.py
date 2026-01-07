from __future__ import annotations

import copy
from pathlib import Path
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
from namel3ss.runtime.execution.normalize import build_plain_text, write_last_execution
from namel3ss.runtime.execution.recorder import record_step
from namel3ss.runtime.execution.calc_index import build_calc_assignment_index
from namel3ss.runtime.memory.api import MemoryManager
from namel3ss.runtime.storage.factory import resolve_store
from namel3ss.schema.identity import IdentitySchema
from namel3ss.schema.records import RecordSchema
from namel3ss.secrets import collect_secret_values, discover_required_secrets_for_profiles
from namel3ss.secrets.context import get_engine_target
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.runtime.api import build_runtime_error
from namel3ss.errors.runtime.model import RuntimeWhere
from namel3ss.outcome.builder import build_outcome_pack
from namel3ss.outcome.model import MemoryOutcome, StateOutcome, StoreOutcome
from namel3ss.runtime.boundary import attach_project_root, attach_secret_values, boundary_from_error, mark_boundary
from namel3ss.tools_with.api import build_tools_pack
from namel3ss.security import activate_security_wall, build_security_wall, redact_sensitive_payload, resolve_secret_values


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
        config: Optional[AppConfig] = None,
        runtime_theme: Optional[str] = None,
        identity_schema: IdentitySchema | None = None,
        identity: dict | None = None,
        project_root: str | None = None,
        app_path: str | None = None,
    ) -> None:
        resolved_config = config or load_config()
        default_ai_provider = ai_provider or MockProvider()
        provider_cache = {"mock": default_ai_provider}
        resolved_store = resolve_store(store, config=resolved_config)
        self._state_loaded_from_store = initial_state is None
        starting_state = initial_state if initial_state is not None else resolved_store.load_state()
        resolved_identity = identity if identity is not None else resolve_identity(resolved_config, identity_schema)
        ai_profiles = ai_profiles or {}
        secrets_map = _build_secrets_map(ai_profiles, resolved_config, app_path)
        self.ctx = ExecutionContext(
            flow=flow,
            schemas=schemas or {},
            state=starting_state or {},
            locals={"input": input_data or {}, "secrets": secrets_map},
            identity=resolved_identity,
            constants=set(),
            last_value=None,
            store=resolved_store,
            ai_provider=default_ai_provider,
            ai_profiles=ai_profiles,
            agents=agents or {},
            tools=tools or {},
            functions=functions or {},
            traces=[],
            memory_manager=memory_manager or MemoryManager(project_root=project_root, app_path=app_path),
            agent_calls=0,
            config=resolved_config,
            provider_cache=provider_cache,
            runtime_theme=runtime_theme,
            project_root=project_root,
            app_path=app_path,
            record_changes=[],
            execution_steps=[],
            execution_step_counter=0,
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

    def run(self) -> ExecutionResult:
        wall = build_security_wall(self.ctx.config, self.ctx.traces)
        with activate_security_wall(wall):
            return self._run_internal()

    def _run_internal(self) -> ExecutionResult:
        record_step(
            self.ctx,
            kind="flow_start",
            what=f'flow "{self.ctx.flow.name}" started',
            line=self.ctx.flow.line,
            column=self.ctx.flow.column,
        )
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
            try:
                self.ctx.store.begin()
                store_began = True
            except Exception as err:
                mark_boundary(err, "store", action="begin")
                raise
            store_started = True
            try:
                for idx, stmt in enumerate(self.ctx.flow.body, start=1):
                    self.ctx.current_statement = stmt
                    self.ctx.current_statement_index = idx
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
            if (
                isinstance(exc, Namel3ssError)
                and isinstance(exc.details, dict)
                and exc.details.get("error_id")
            ):
                details["cause"] = exc.details
            raise Namel3ssError(
                message,
                line=where.line,
                column=where.column,
                details=details,
            ) from exc
        finally:
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
            runtime_theme=self.ctx.runtime_theme,
        )


def _record_flow_end(ctx: ExecutionContext, *, ok: bool) -> None:
    record_step(
        ctx,
        kind="flow_end",
        what=f'flow "{ctx.flow.name}" ended',
        because="completed successfully" if ok else "ended with error",
        line=ctx.flow.line,
        column=ctx.flow.column,
    )


def _record_error_step(ctx: ExecutionContext, error: Exception) -> None:
    line = getattr(error, "line", None)
    column = getattr(error, "column", None)
    if isinstance(error, Namel3ssError):
        line = error.line
        column = error.column
    record_step(
        ctx,
        kind="error",
        what=f"error {error.__class__.__name__}",
        because=str(error),
        line=line,
        column=column,
    )



def _persist_execution_artifacts(ctx: ExecutionContext, *, ok: bool, error: Exception | None) -> None:
    if not ctx.project_root:
        return
    try:
        pack = _build_execution_pack(ctx, ok=ok, error=error)
        secret_values = resolve_secret_values(config=ctx.config)
        redacted = redact_sensitive_payload(pack, secret_values)
        plain_text = build_plain_text(redacted if isinstance(redacted, dict) else pack)
        write_last_execution(Path(ctx.project_root), redacted, plain_text)
    except Exception:
        return


def _build_execution_pack(ctx: ExecutionContext, *, ok: bool, error: Exception | None) -> dict:
    steps = list(ctx.execution_steps or [])
    traces = _trace_summaries(ctx.traces)
    summary = _summary_text(ctx.flow.name, ok=ok, error=error, step_count=len(steps))
    pack = {
        "ok": ok,
        "flow_name": ctx.flow.name,
        "execution_steps": steps,
        "traces": traces,
        "summary": summary,
    }
    if error:
        pack["error"] = {
            "kind": error.__class__.__name__,
            "message": str(error),
        }
    return pack


def _write_run_outcome(
    ctx: ExecutionContext,
    *,
    store_began: bool,
    store_committed: bool,
    store_commit_failed: bool,
    store_rolled_back: bool,
    store_rollback_failed: bool,
    state_save_attempted: bool,
    state_save_succeeded: bool,
    state_save_failed: bool,
    memory_persist_attempted: bool,
    memory_persist_succeeded: bool,
    memory_persist_failed: bool,
    error_escaped: bool,
    state_loaded_from_store: bool | None,
) -> None:
    store = StoreOutcome(
        began=store_began,
        committed=store_committed,
        commit_failed=store_commit_failed,
        rolled_back=store_rolled_back,
        rollback_failed=store_rollback_failed,
    )
    state = StateOutcome(
        loaded_from_store=state_loaded_from_store,
        save_attempted=state_save_attempted,
        save_succeeded=state_save_succeeded,
        save_failed=state_save_failed,
    )
    memory = MemoryOutcome(
        persist_attempted=memory_persist_attempted,
        persist_succeeded=memory_persist_succeeded,
        persist_failed=memory_persist_failed,
        skipped_reason=None,
    )
    try:
        build_outcome_pack(
            flow_name=ctx.flow.name,
            store=store,
            state=state,
            memory=memory,
            record_changes_count=len(ctx.record_changes or []),
            execution_steps_count=len(ctx.execution_steps or []),
            traces_count=len(ctx.traces or []),
            error_escaped=error_escaped,
            project_root=ctx.project_root,
        )
    except Exception:
        return


def _write_tools_with_pack(ctx: ExecutionContext) -> None:
    if not ctx.project_root:
        return
    try:
        build_tools_pack(ctx.traces, project_root=ctx.project_root)
    except Exception:
        return


def _summary_text(flow_name: str, *, ok: bool, error: Exception | None, step_count: int) -> str:
    if ok:
        return f'Flow "{flow_name}" ran with {step_count} steps.'
    error_kind = error.__class__.__name__ if error else "error"
    return f'Flow "{flow_name}" failed with {error_kind}.'


def _trace_summaries(traces: list) -> list[dict]:
    summaries: list[dict] = []
    for trace in traces:
        summaries.append(
            {
                "ai_name": getattr(trace, "ai_name", None),
                "events": len(getattr(trace, "canonical_events", []) or []),
                "tool_calls": len(getattr(trace, "tool_calls", []) or []),
            }
        )
    return summaries


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
    if isinstance(stmt, ir.ThemeChange):
        return "theme"
    if isinstance(stmt, ir.RunAgentStmt):
        return "run_agent"
    if isinstance(stmt, ir.RunAgentsParallelStmt):
        return "run_agents_parallel"
    if isinstance(stmt, ir.ParallelBlock):
        return "parallel"
    return None


def _dict_traces(traces: list) -> list[dict]:
    return [trace for trace in traces if isinstance(trace, dict)]


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
