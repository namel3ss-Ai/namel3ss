from __future__ import annotations

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.composition.flow_calls import _run_flow
from namel3ss.runtime.execution.recorder import record_step
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.executor.expr_eval import evaluate_expression


def execute_ai_metadata_flow(ctx: ExecutionContext) -> object:
    metadata = getattr(ctx.flow, "ai_metadata", None)
    if metadata is None:
        raise Namel3ssError("Flow has no AI metadata.", line=ctx.flow.line, column=ctx.flow.column)
    kind = str(getattr(metadata, "kind", "llm_call") or "llm_call")
    if kind == "chain":
        return _execute_chain_flow(ctx, metadata)
    return _execute_pattern_flow(ctx, metadata, kind=kind)


def _execute_pattern_flow(ctx: ExecutionContext, metadata, *, kind: str) -> object:
    model = str(getattr(metadata, "model", "") or "").strip()
    if not model:
        raise Namel3ssError("AI flow is missing model metadata.", line=ctx.flow.line, column=ctx.flow.column)
    prompt = _resolve_prompt(ctx, metadata, kind=kind)
    user_input = _input_text(ctx)
    output_text = _ask_provider(ctx, model=model, prompt=prompt, user_input=user_input)
    result = _coerce_pattern_output(metadata, kind=kind, output_text=output_text)
    record_step(
        ctx,
        kind="ai_pattern",
        what=f"ran {kind} pattern",
        data={"model": model, "pattern": kind},
        line=ctx.flow.line,
        column=ctx.flow.column,
    )
    ctx.last_value = result
    return result


def _execute_chain_flow(ctx: ExecutionContext, metadata) -> object:
    steps = list(getattr(metadata, "chain_steps", None) or [])
    if not steps:
        raise Namel3ssError("Chain flow has no steps.", line=ctx.flow.line, column=ctx.flow.column)
    step_outputs: dict[str, object] = {}
    last_output: object = None
    for index, step in enumerate(steps, start=1):
        flow_name = str(getattr(step, "flow_name", "") or "").strip()
        if not flow_name:
            raise Namel3ssError("Chain step is missing flow name.", line=step.line, column=step.column)
        if flow_name not in ctx.flow_map:
            raise Namel3ssError(
                f'Chain step calls unknown flow "{flow_name}".',
                line=step.line,
                column=step.column,
            )
        step_input = evaluate_expression(ctx, step.input_expr)
        input_payload = step_input if isinstance(step_input, dict) else {"value": step_input}
        flow = ctx.flow_map[flow_name]
        flow_call_id = f"chain.{ctx.flow.name}.{index:03d}"
        last_output = _run_flow(ctx, flow, input_payload, flow_call_id)
        step_outputs[flow_name] = {"result": last_output}
        ctx.locals[flow_name] = step_outputs[flow_name]
        record_step(
            ctx,
            kind="chain_step",
            what=f'ran chain step "{flow_name}"',
            data={"step": index, "flow": flow_name},
            line=step.line or ctx.flow.line,
            column=step.column or ctx.flow.column,
        )
    output_fields = list(getattr(metadata, "output_fields", None) or [])
    if not output_fields:
        ctx.last_value = last_output
        return last_output
    payload: dict[str, object] = {}
    for field_index, field in enumerate(output_fields):
        if isinstance(last_output, dict) and field.name in last_output:
            payload[field.name] = last_output[field.name]
            continue
        if field_index == 0:
            payload[field.name] = last_output
            continue
        payload[field.name] = None
    ctx.last_value = payload
    return payload


def _resolve_prompt(ctx: ExecutionContext, metadata, *, kind: str) -> str:
    prompt_expr = getattr(metadata, "prompt_expr", None)
    if prompt_expr is not None:
        value = evaluate_expression(ctx, prompt_expr)
        base = str(value)
    else:
        base = str(getattr(metadata, "prompt", "") or "")
    payload = ctx.locals.get("input", {})
    if kind == "translate":
        source = str(getattr(metadata, "source_language", "") or "")
        target = str(getattr(metadata, "target_language", "") or "")
        text = _field_text(payload, "text")
        if base.strip():
            return base
        return "Translate from " + source + " to " + target + ":\n" + text
    if kind == "qa":
        if base.strip():
            return base
        question = _field_text(payload, "question")
        context = _field_text(payload, "context")
        return "Qn: " + question + "\nCtx: " + context + "\nAns: "
    if kind == "cot":
        if base.strip():
            return "Let's think step by step.\n" + base
        problem = _field_text(payload, "problem")
        return "Let's think step by step.\nQn: " + problem + "\nAns: "
    return base


def _field_text(payload: object, key: str) -> str:
    if not isinstance(payload, dict):
        return ""
    value = payload.get(key)
    return str(value) if value is not None else ""


def _input_text(ctx: ExecutionContext) -> str:
    payload = ctx.locals.get("input")
    if isinstance(payload, str):
        return payload
    return canonical_json_dumps(payload, pretty=False, drop_run_keys=False)


def _ask_provider(ctx: ExecutionContext, *, model: str, prompt: str, user_input: str) -> str:
    provider = ctx.ai_provider
    response = provider.ask(
        model=model,
        system_prompt=prompt,
        user_input=user_input,
        tools=[],
        memory=None,
        tool_results=None,
    )
    output = response.output if hasattr(response, "output") else response
    return str(output)


def _coerce_pattern_output(metadata, *, kind: str, output_text: str) -> object:
    output_fields = list(getattr(metadata, "output_fields", None) or [])
    if output_fields:
        result: dict[str, object] = {}
        for field in output_fields:
            result[field.name] = _typed_value(field.type_name, _field_default_value(field.name, kind, output_text))
        return result
    output_type = str(getattr(metadata, "output_type", "") or "text")
    return _typed_value(output_type, output_text)


def _field_default_value(name: str, kind: str, output_text: str) -> object:
    normalized = name.strip().lower()
    if kind == "qa":
        if normalized in {"ans", "answer"}:
            return output_text
        if normalized == "confidence":
            return 0.0
        return output_text
    if kind == "cot":
        if normalized == "reasoning":
            return output_text
        if normalized in {"ans", "answer"}:
            return output_text
        return output_text
    return output_text


def _typed_value(type_name: str, value: object) -> object:
    normalized = str(type_name or "text").strip().lower()
    if normalized.startswith("list<"):
        if isinstance(value, list):
            return list(value)
        return [value]
    if normalized == "number":
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(str(value).strip())
        except Exception:
            return 0.0
    if normalized == "boolean":
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in {"true", "yes", "1"}:
            return True
        if text in {"false", "no", "0"}:
            return False
        return False
    if normalized == "json":
        if isinstance(value, dict):
            return dict(value)
        return {"value": value}
    return str(value)


__all__ = ["execute_ai_metadata_flow"]
