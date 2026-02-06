from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ingestion.policy import (
    ACTION_INGESTION_OVERRIDE,
    ACTION_INGESTION_RUN,
    ACTION_RETRIEVAL_INCLUDE_WARN,
    evaluate_ingestion_policy,
    load_ingestion_policy,
    policy_error,
    policy_trace,
)
from namel3ss.ir import nodes as ir
from namel3ss.pipelines.model import PipelineStepResult, pipeline_step_id
from namel3ss.pipelines.registry import pipeline_definitions
from namel3ss.pipelines.runner import run_pipeline
from namel3ss.runtime.answer.traces import (
    answer_explain_from_error,
    answer_trace_from_error,
    answer_trace_from_steps,
    build_answer_explain_trace,
)
from namel3ss.runtime.composition.retrieval_explain_logging import (
    build_retrieval_explain_metadata,
)
from namel3ss.runtime.explainability.logger import append_explain_entry
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.execution.recorder import record_step
from namel3ss.runtime.values.coerce import require_type
from namel3ss.traces.schema import TraceEventType


def execute_pipeline_call(
    ctx: ExecutionContext,
    expr: ir.CallPipelineExpr,
    evaluate_expression,
    collector=None,
) -> object:
    if getattr(ctx, "call_stack", []):
        raise Namel3ssError("Functions cannot call pipelines", line=expr.line, column=expr.column)
    contract = _lookup_pipeline_contract(ctx, expr.pipeline_name, line=expr.line, column=expr.column)
    args_by_name = _evaluate_call_args(ctx, expr.arguments, evaluate_expression, collector)
    input_payload = _build_input_payload(contract.signature, args_by_name, expr)

    record_step(
        ctx,
        kind="pipeline_call_start",
        what=f'call pipeline "{expr.pipeline_name}"',
        data={"pipeline": expr.pipeline_name},
        line=expr.line,
        column=expr.column,
    )
    try:
        definition = pipeline_definitions().get(expr.pipeline_name)
        if definition is not None:
            _record_pipeline_started(ctx, expr.pipeline_name, definition)
        output_map, steps = _run_pipeline(ctx, expr.pipeline_name, input_payload, expr)
        output_map = _validate_pipeline_output(contract.signature, output_map, expr)
        _record_pipeline_steps(ctx, expr.pipeline_name, steps, expr)
        selected = _select_outputs(output_map, expr.outputs, expr)
    except Exception as exc:
        _record_pipeline_finished(ctx, expr.pipeline_name, status="error", error=exc)
        record_step(
            ctx,
            kind="pipeline_call_error",
            what=f'call pipeline "{expr.pipeline_name}" failed',
            because=str(exc),
            data={"pipeline": expr.pipeline_name},
            line=expr.line,
            column=expr.column,
        )
        raise
    _record_pipeline_finished(ctx, expr.pipeline_name, status="ok", error=None)
    record_step(
        ctx,
        kind="pipeline_call_end",
        what=f'call pipeline "{expr.pipeline_name}" finished',
        data={"pipeline": expr.pipeline_name},
        line=expr.line,
        column=expr.column,
    )
    return selected


def _run_pipeline(
    ctx: ExecutionContext,
    name: str,
    payload: dict,
    expr: ir.CallPipelineExpr,
) -> tuple[dict, list[PipelineStepResult]]:
    if name == "ingestion":
        return _run_ingestion(ctx, payload, expr)
    if name == "retrieval":
        return _run_retrieval(ctx, payload, expr)
    if name == "answer":
        return _run_answer(ctx, payload, expr)
    raise Namel3ssError(
        build_guidance_message(
            what=f'Unknown pipeline "{name}".',
            why="Pipeline calls must reference a known pipeline.",
            fix="Use a supported pipeline name.",
            example='call pipeline "retrieval":\n  input:\n    query is "invoice"\n  output:\n    report',
        ),
        line=expr.line,
        column=expr.column,
    )


def _run_ingestion(ctx: ExecutionContext, payload: dict, expr: ir.CallPipelineExpr) -> tuple[dict, list[PipelineStepResult]]:
    _require_uploads_capability(ctx, expr)
    policy = load_ingestion_policy(
        project_root=ctx.project_root,
        app_path=ctx.app_path,
        policy_decl=getattr(ctx, "policy", None),
    )
    decision = evaluate_ingestion_policy(policy, ACTION_INGESTION_RUN, ctx.identity)
    ctx.traces.append(policy_trace(ACTION_INGESTION_RUN, decision))
    if not decision.allowed:
        raise policy_error(ACTION_INGESTION_RUN, decision)

    mode_value = payload.get("mode")
    mode_text = str(mode_value).strip().lower() if isinstance(mode_value, str) else ""
    if mode_text in {"layout", "ocr"}:
        override = evaluate_ingestion_policy(policy, ACTION_INGESTION_OVERRIDE, ctx.identity)
        ctx.traces.append(policy_trace(ACTION_INGESTION_OVERRIDE, override))
        if not override.allowed:
            raise policy_error(ACTION_INGESTION_OVERRIDE, override, mode=mode_text)

    _apply_ingestion_overrides(ctx.state, payload)
    result = run_pipeline(ctx, name="ingestion", payload=payload)
    output = result.output
    report = output.get("report") if isinstance(output, dict) else None
    if not isinstance(report, dict):
        raise Namel3ssError("Ingestion report is missing.", line=expr.line, column=expr.column)
    ctx.traces.extend(_ingestion_traces(report))
    return output, result.steps


def _run_retrieval(ctx: ExecutionContext, payload: dict, expr: ir.CallPipelineExpr) -> tuple[dict, list[PipelineStepResult]]:
    _require_uploads_capability(ctx, expr)
    policy = load_ingestion_policy(
        project_root=ctx.project_root,
        app_path=ctx.app_path,
        policy_decl=getattr(ctx, "policy", None),
    )
    decision = evaluate_ingestion_policy(policy, ACTION_RETRIEVAL_INCLUDE_WARN, ctx.identity)
    ctx.traces.append(policy_trace(ACTION_RETRIEVAL_INCLUDE_WARN, decision))

    result = run_pipeline(ctx, name="retrieval", payload=payload)
    output = result.output
    report = output.get("report") if isinstance(output, dict) else None
    if isinstance(report, dict):
        report = dict(report)
        report["warn_policy"] = {
            "action": ACTION_RETRIEVAL_INCLUDE_WARN,
            "decision": "allowed" if decision.allowed else "denied",
            "reason": decision.reason,
        }
        output["report"] = report
        results = report.get("results")
        append_explain_entry(
            ctx,
            stage="retrieval",
            event_type="selected_chunks",
            inputs={"query": report.get("query")},
            outputs={"result_count": len(results) if isinstance(results, list) else 0},
            metadata=build_retrieval_explain_metadata(report),
        )
    ctx.traces.extend(_retrieval_traces(report if isinstance(report, dict) else {}))
    return output, result.steps


def _run_answer(ctx: ExecutionContext, payload: dict, expr: ir.CallPipelineExpr) -> tuple[dict, list[PipelineStepResult]]:
    _require_uploads_capability(ctx, expr)
    policy = load_ingestion_policy(
        project_root=ctx.project_root,
        app_path=ctx.app_path,
        policy_decl=getattr(ctx, "policy", None),
    )
    decision = evaluate_ingestion_policy(policy, ACTION_RETRIEVAL_INCLUDE_WARN, ctx.identity)
    ctx.traces.append(policy_trace(ACTION_RETRIEVAL_INCLUDE_WARN, decision))
    try:
        result = run_pipeline(ctx, name="answer", payload=payload)
    except Exception as exc:
        trace = answer_trace_from_error(exc)
        if trace is not None:
            ctx.traces.append(trace)
        explain_trace = answer_explain_from_error(exc)
        if explain_trace is not None:
            ctx.traces.append(explain_trace)
        raise
    output = result.output
    report = output.get("report") if isinstance(output, dict) else None
    if not isinstance(report, dict):
        raise Namel3ssError("Answer report is missing.", line=expr.line, column=expr.column)
    trace = answer_trace_from_steps(result.steps)
    if trace is not None:
        ctx.traces.append(trace)
    explain_bundle = report.get("explain")
    if isinstance(explain_bundle, dict):
        ctx.traces.append(build_answer_explain_trace(explain_bundle))
    return output, result.steps


def _apply_ingestion_overrides(state: dict, payload: dict) -> None:
    if "ingestion" in payload:
        state["ingestion"] = payload.get("ingestion")
    if "index" in payload:
        state["index"] = payload.get("index")


def _record_pipeline_started(ctx: ExecutionContext, pipeline_name: str, definition) -> None:
    ctx.traces.append(
        {
            "type": TraceEventType.PIPELINE_STARTED,
            "pipeline": pipeline_name,
            "steps": [
                {
                    "step_id": pipeline_step_id(pipeline_name, step.kind, ordinal),
                    "step_kind": step.kind,
                    "ordinal": ordinal,
                }
                for ordinal, step in enumerate(definition.steps, start=1)
            ],
        }
    )


def _record_pipeline_steps(
    ctx: ExecutionContext,
    pipeline_name: str,
    steps: list[PipelineStepResult],
    expr: ir.CallPipelineExpr,
) -> None:
    for step in steps:
        ctx.traces.append(
            {
                "type": TraceEventType.PIPELINE_STEP,
                "pipeline": pipeline_name,
                "step_id": step.step_id,
                "step_kind": step.kind,
                "status": step.status,
                "summary": step.summary,
                "checksum": step.checksum,
                "ordinal": step.ordinal,
            }
        )
        record_step(
            ctx,
            kind="pipeline_step",
            what=f'pipeline "{pipeline_name}" {step.kind}',
            data={
                "pipeline": pipeline_name,
                "step_id": step.step_id,
                "step_kind": step.kind,
                "status": step.status,
                "summary": step.summary,
                "checksum": step.checksum,
                "step_ordinal": step.ordinal,
            },
            line=expr.line,
            column=expr.column,
        )


def _record_pipeline_finished(
    ctx: ExecutionContext,
    pipeline_name: str,
    *,
    status: str,
    error: Exception | None,
) -> None:
    event = {
        "type": TraceEventType.PIPELINE_FINISHED,
        "pipeline": pipeline_name,
        "status": status,
    }
    if error is not None:
        event["error_message"] = str(error)
    ctx.traces.append(event)


def _evaluate_call_args(ctx: ExecutionContext, arguments: list[ir.CallArg], evaluate_expression, collector=None) -> dict[str, object]:
    args_by_name: dict[str, object] = {}
    for arg in arguments:
        if arg.name in args_by_name:
            raise Namel3ssError(
                f"Duplicate pipeline input '{arg.name}'",
                line=arg.line,
                column=arg.column,
            )
        args_by_name[arg.name] = evaluate_expression(ctx, arg.value, collector)
    return args_by_name


def _build_input_payload(signature: ir.FunctionSignature, args_by_name: dict[str, object], expr: ir.CallPipelineExpr) -> dict[str, object]:
    payload: dict[str, object] = {}
    for param in signature.inputs:
        if param.name not in args_by_name:
            if param.required:
                raise Namel3ssError(
                    f"Missing pipeline input '{param.name}'",
                    line=expr.line,
                    column=expr.column,
                )
            continue
        value = args_by_name[param.name]
        require_type(value, param.type_name, line=expr.line, column=expr.column)
        payload[param.name] = value
    extra_args = set(args_by_name.keys()) - {param.name for param in signature.inputs}
    if extra_args:
        name = sorted(extra_args)[0]
        raise Namel3ssError(
            f"Unknown pipeline input '{name}'",
            line=expr.line,
            column=expr.column,
        )
    return payload


def _validate_pipeline_output(signature: ir.FunctionSignature, value: object, expr: ir.CallPipelineExpr) -> dict:
    if not isinstance(value, dict):
        raise Namel3ssError(
            "Pipeline output must be a map",
            line=expr.line,
            column=expr.column,
        )
    output_map: dict = dict(value)
    expected = {param.name: param for param in signature.outputs or []}
    for name, param in expected.items():
        if name not in output_map:
            if not param.required:
                continue
            raise Namel3ssError(
                f"Missing pipeline output '{name}'",
                line=expr.line,
                column=expr.column,
            )
        require_type(output_map[name], param.type_name, line=expr.line, column=expr.column)
    extra_keys = set(output_map.keys()) - set(expected.keys())
    if extra_keys:
        name = sorted(extra_keys)[0]
        raise Namel3ssError(
            f"Unknown pipeline output '{name}'",
            line=expr.line,
            column=expr.column,
        )
    return output_map


def _select_outputs(output_map: dict, output_names: list[str], expr: ir.CallPipelineExpr) -> dict:
    selected: dict[str, object] = {}
    for name in output_names:
        if name not in output_map:
            raise Namel3ssError(
                f"Missing pipeline output '{name}'",
                line=expr.line,
                column=expr.column,
            )
        selected[name] = output_map[name]
    return selected


def _lookup_pipeline_contract(ctx: ExecutionContext, name: str, *, line: int | None, column: int | None) -> ir.ContractDecl:
    contract = ctx.pipeline_contracts.get(name)
    if contract is not None:
        return contract
    raise Namel3ssError(
        build_guidance_message(
            what=f'Unknown pipeline "{name}".',
            why="Pipeline calls must reference a known pipeline.",
            fix="Use a supported pipeline name.",
            example='call pipeline "retrieval":\n  input:\n    query is "invoice"\n  output:\n    report',
        ),
        line=line,
        column=column,
    )


def _require_uploads_capability(ctx: ExecutionContext, expr: ir.CallPipelineExpr) -> None:
    caps = getattr(ctx, "capabilities", ()) or ()
    if "uploads" in caps:
        return
    raise Namel3ssError(
        build_guidance_message(
            what="Uploads capability is not enabled.",
            why="Pipelines for ingestion and retrieval require the uploads capability.",
            fix="Add uploads to the capabilities block in app.ai.",
            example="capabilities:\n  uploads",
        ),
        line=expr.line,
        column=expr.column,
    )


def _ingestion_traces(report: dict) -> list[dict]:
    upload_id = report.get("upload_id")
    detected = report.get("detected")
    method_used = report.get("method_used")
    status = report.get("status")
    reasons = report.get("reasons")
    provenance = report.get("provenance") if isinstance(report.get("provenance"), dict) else {}
    source_name = provenance.get("source_name") if isinstance(provenance, dict) else None
    traces = [
        {
            "type": TraceEventType.INGESTION_STARTED,
            "upload_id": upload_id,
            "method": method_used,
            "detected": detected,
            "source_name": source_name,
        },
    ]
    traces.extend(_progress_traces(report))
    traces.append(
        {
            "type": TraceEventType.INGESTION_QUALITY_GATE,
            "upload_id": upload_id,
            "status": status,
            "reasons": reasons,
            "source_name": source_name,
        }
    )
    return traces


def _progress_traces(report: dict) -> list[dict]:
    events = report.get("progress")
    if not isinstance(events, list):
        return []
    traces: list[dict] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        if event.get("phase") != "quick":
            continue
        trace = {
            "type": TraceEventType.INGESTION_PROGRESS,
            "title": event.get("title"),
            "upload_id": event.get("upload_id"),
            "source_name": event.get("source_name"),
            "ingestion_phase": event.get("phase"),
        }
        if "status" in event:
            trace["status"] = event.get("status")
        traces.append(trace)
    return traces


def _retrieval_traces(result: dict) -> list[dict]:
    preferred = result.get("preferred_quality") if isinstance(result, dict) else None
    included_warn = result.get("included_warn") if isinstance(result, dict) else None
    excluded_blocked = result.get("excluded_blocked") if isinstance(result, dict) else None
    warn_allowed = result.get("warn_allowed") if isinstance(result, dict) else None
    excluded_warn = result.get("excluded_warn") if isinstance(result, dict) else None
    warn_policy = result.get("warn_policy") if isinstance(result, dict) else None
    tier = result.get("tier") if isinstance(result, dict) else None
    return [
        {
            "type": TraceEventType.RETRIEVAL_STARTED,
        },
        {
            "type": TraceEventType.RETRIEVAL_TIER_SELECTED,
            "tier": tier.get("requested") if isinstance(tier, dict) else None,
            "selected": tier.get("selected") if isinstance(tier, dict) else None,
            "reason": tier.get("reason") if isinstance(tier, dict) else None,
            "available": tier.get("available") if isinstance(tier, dict) else None,
            "counts": tier.get("counts") if isinstance(tier, dict) else None,
        },
        {
            "type": TraceEventType.RETRIEVAL_QUALITY_POLICY,
            "preferred": preferred,
            "included_warn": included_warn,
            "excluded_blocked": excluded_blocked,
            "warn_allowed": warn_allowed,
            "excluded_warn": excluded_warn,
            "warn_policy": warn_policy,
        },
    ]




__all__ = ["execute_pipeline_call"]
