from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ingestion.api import run_ingestion
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
from namel3ss.retrieval.api import run_retrieval
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.execution.recorder import record_step
from namel3ss.runtime.values.coerce import require_type
from namel3ss.secrets import collect_secret_values
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
        output_map = _run_pipeline(ctx, expr.pipeline_name, input_payload, expr)
        output_map = _validate_pipeline_output(contract.signature, output_map, expr)
        selected = _select_outputs(output_map, expr.outputs, expr)
    except Exception as exc:
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
    record_step(
        ctx,
        kind="pipeline_call_end",
        what=f'call pipeline "{expr.pipeline_name}" finished',
        data={"pipeline": expr.pipeline_name},
        line=expr.line,
        column=expr.column,
    )
    return selected


def _run_pipeline(ctx: ExecutionContext, name: str, payload: dict, expr: ir.CallPipelineExpr) -> dict:
    if name == "ingestion":
        return _run_ingestion(ctx, payload, expr)
    if name == "retrieval":
        return _run_retrieval(ctx, payload, expr)
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


def _run_ingestion(ctx: ExecutionContext, payload: dict, expr: ir.CallPipelineExpr) -> dict:
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
    secret_values = collect_secret_values(ctx.config)
    result = run_ingestion(
        upload_id=str(payload.get("upload_id") or ""),
        mode=str(payload.get("mode")) if isinstance(payload.get("mode"), str) else None,
        state=ctx.state,
        project_root=ctx.project_root,
        app_path=ctx.app_path,
        secret_values=secret_values,
    )
    report = result.get("report") if isinstance(result, dict) else None
    if not isinstance(report, dict):
        raise Namel3ssError("Ingestion report is missing.", line=expr.line, column=expr.column)
    ctx.traces.extend(_ingestion_traces(report))
    return {
        "report": report,
        "ingestion": ctx.state.get("ingestion"),
        "index": ctx.state.get("index"),
    }


def _run_retrieval(ctx: ExecutionContext, payload: dict, expr: ir.CallPipelineExpr) -> dict:
    _require_uploads_capability(ctx, expr)
    policy = load_ingestion_policy(
        project_root=ctx.project_root,
        app_path=ctx.app_path,
        policy_decl=getattr(ctx, "policy", None),
    )
    decision = evaluate_ingestion_policy(policy, ACTION_RETRIEVAL_INCLUDE_WARN, ctx.identity)
    ctx.traces.append(policy_trace(ACTION_RETRIEVAL_INCLUDE_WARN, decision))

    secret_values = collect_secret_values(ctx.config)
    state_view = _retrieval_state_view(ctx.state, payload)
    result = run_retrieval(
        query=payload.get("query"),
        limit=payload.get("limit"),
        state=state_view,
        project_root=ctx.project_root,
        app_path=ctx.app_path,
        secret_values=secret_values,
        identity=ctx.identity,
        policy_decision=decision,
    )
    ctx.traces.extend(_retrieval_traces(result))
    return {"report": result}


def _retrieval_state_view(state: dict, payload: dict) -> dict:
    if "ingestion" not in payload and "index" not in payload:
        return state
    view = dict(state)
    if "ingestion" in payload:
        view["ingestion"] = payload.get("ingestion")
    if "index" in payload:
        view["index"] = payload.get("index")
    return view


def _apply_ingestion_overrides(state: dict, payload: dict) -> None:
    if "ingestion" in payload:
        state["ingestion"] = payload.get("ingestion")
    if "index" in payload:
        state["index"] = payload.get("index")


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
    return [
        {
            "type": TraceEventType.INGESTION_STARTED,
            "upload_id": upload_id,
            "method": method_used,
            "detected": detected,
        },
        {
            "type": TraceEventType.INGESTION_QUALITY_GATE,
            "upload_id": upload_id,
            "status": status,
            "reasons": reasons,
        },
    ]


def _retrieval_traces(result: dict) -> list[dict]:
    preferred = result.get("preferred_quality") if isinstance(result, dict) else None
    included_warn = result.get("included_warn") if isinstance(result, dict) else None
    excluded_blocked = result.get("excluded_blocked") if isinstance(result, dict) else None
    warn_allowed = result.get("warn_allowed") if isinstance(result, dict) else None
    excluded_warn = result.get("excluded_warn") if isinstance(result, dict) else None
    warn_policy = result.get("warn_policy") if isinstance(result, dict) else None
    return [
        {
            "type": TraceEventType.RETRIEVAL_STARTED,
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
