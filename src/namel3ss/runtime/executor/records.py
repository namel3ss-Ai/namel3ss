from __future__ import annotations

from pathlib import Path

from namel3ss.outcome.builder import build_outcome_pack
from namel3ss.outcome.model import MemoryOutcome, StateOutcome, StoreOutcome
from namel3ss.runtime.execution.normalize import build_plain_text, write_last_execution
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.executor.traces import _trace_summaries
from namel3ss.runtime.explainability.logger import persist_explain_log
from namel3ss.observability.trace_runs import write_trace_run
from namel3ss.tools_with.api import build_tools_pack
from namel3ss.schema.evolution import write_workspace_snapshot
from namel3ss.security import redact_sensitive_payload, resolve_secret_values
from namel3ss.runtime.security.encryption_utils import encrypt_execution_pack


def _persist_execution_artifacts(ctx: ExecutionContext, *, ok: bool, error: Exception | None) -> None:
    if not ctx.project_root:
        return
    try:
        steps = list(ctx.execution_steps or [])
        pack = _build_execution_pack(ctx, ok=ok, error=error)
        secret_values = resolve_secret_values(config=ctx.config)
        redacted = redact_sensitive_payload(pack, secret_values)
        encrypted = redacted
        if ctx.sensitive and ctx.encryption_service and isinstance(redacted, dict):
            encrypted = encrypt_execution_pack(redacted, ctx.encryption_service)
        plain_text = build_plain_text(encrypted if isinstance(encrypted, dict) else pack)
        write_last_execution(Path(ctx.project_root), encrypted, plain_text)
        write_trace_run(
            project_root=ctx.project_root,
            app_path=ctx.app_path,
            flow_name=ctx.flow.name,
            steps=steps,
            secret_values=secret_values,
        )
        if ok:
            write_workspace_snapshot(
                ctx.schemas.values(),
                project_root=ctx.project_root,
                store=ctx.store,
            )
        persist_explain_log(ctx)
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


__all__ = ["_persist_execution_artifacts", "_write_run_outcome", "_write_tools_with_pack"]
