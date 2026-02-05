from __future__ import annotations

from pathlib import Path

from namel3ss.observability.ai_metrics import build_ai_record, record_ai_metric
from namel3ss.observability.enablement import observability_enabled
from namel3ss.observe import record_event, summarize_value
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.security.encryption_utils import encrypt_ai_record
from namel3ss.secrets import collect_secret_values


def record_ai_event(
    ctx: ExecutionContext,
    ai_name: str,
    provider: str,
    model: str,
    *,
    status: str,
    input_text: str,
    output_text: str | None,
    started_at: float,
    duration_ms: int,
    error: Exception | None = None,
) -> None:
    if getattr(ctx, "sensitive", False):
        return
    if not ctx.project_root:
        return
    secret_values = collect_secret_values(ctx.config)
    event = {
        "type": "ai_call",
        "flow_name": getattr(ctx.flow, "name", None),
        "ai_name": ai_name,
        "provider": provider,
        "model": model,
        "status": status,
        "time_start": started_at,
        "time_end": started_at + (duration_ms / 1000.0),
        "duration_ms": duration_ms,
        "redacted_input_summary": summarize_value(input_text, secret_values=secret_values),
        "redacted_output_summary": summarize_value(output_text or "", secret_values=secret_values),
    }
    if error:
        event["error_type"] = error.__class__.__name__
        event["error_message"] = str(error)
    record_event(Path(ctx.project_root), event, secret_values=secret_values)


def record_ai_metrics(
    ctx: ExecutionContext,
    *,
    input_text: str,
    output_text: str,
    start_step: int,
) -> None:
    if not observability_enabled():
        return
    kind = _ai_flow_kind(ctx)
    expected = _expected_label(ctx)
    accuracy = None
    if kind == "classification" and expected is not None:
        accuracy = 1.0 if output_text.strip().lower() == expected.strip().lower() else 0.0
    end_step = getattr(ctx, "execution_step_counter", 0)
    latency_steps = max(0, int(end_step) - int(start_step))
    record = build_ai_record(
        flow_name=getattr(ctx.flow, "name", ""),
        kind=kind,
        input_text=input_text,
        output_text=output_text,
        expected=expected,
        accuracy=accuracy,
        latency_steps=latency_steps,
        prompt_tokens=None,
        completion_tokens=None,
    )
    if ctx.sensitive and ctx.encryption_service:
        record = encrypt_ai_record(record, ctx.encryption_service)
    record_ai_metric(
        project_root=getattr(ctx, "project_root", None),
        app_path=getattr(ctx, "app_path", None),
        record=record,
    )


def _ai_flow_kind(ctx: ExecutionContext) -> str:
    meta = getattr(ctx.flow, "ai_metadata", None)
    kind = getattr(meta, "kind", None) if meta is not None else None
    if isinstance(kind, str) and kind:
        return kind
    return "llm_call"


def _expected_label(ctx: ExecutionContext) -> str | None:
    input_payload = ctx.locals.get("input") if isinstance(ctx.locals, dict) else None
    if not isinstance(input_payload, dict):
        return None
    for key in ("expected", "expected_label", "label"):
        value = input_payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


__all__ = ["record_ai_event", "record_ai_metrics"]
