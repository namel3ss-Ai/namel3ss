from __future__ import annotations

from pathlib import Path

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.models import load_model_registry


_AI_FLOW_KINDS = {
    "llm_call",
    "rag",
    "classification",
    "summarise",
    "translate",
    "qa",
    "cot",
    "chain",
}
_ALLOWED_TYPES = {"text", "number", "boolean", "json", "null"}
_ALLOWED_TEST_METRICS = {
    "accuracy",
    "precision",
    "recall",
    "f1",
    "f1_score",
    "rouge",
    "bleu",
    "exact_match",
}


def validate_ai_flows(
    ai_flows: list[ast.AIFlowDefinition],
    *,
    record_names: set[str],
    known_flow_names: set[str] | None = None,
    project_root: str | Path | None = None,
    app_path: str | Path | None = None,
) -> None:
    seen: set[str] = set()
    registry = load_model_registry(project_root, app_path)
    for flow in ai_flows:
        if flow.name in seen:
            raise Namel3ssError(
                build_guidance_message(
                    what=f'AI flow "{flow.name}" is declared more than once.',
                    why="Each AI flow name must be unique.",
                    fix="Rename the duplicate AI flow.",
                    example=f'{flow.kind} "{flow.name}":',
                ),
                line=flow.line,
                column=flow.column,
            )
        seen.add(flow.name)
        if flow.kind not in _AI_FLOW_KINDS:
            raise Namel3ssError(
                build_guidance_message(
                    what=f'AI flow "{flow.name}" has an unknown type.',
                    why="AI flow types are fixed.",
                    fix="Use llm_call, rag, classification, summarise, translate, qa, cot, or chain.",
                    example='qa "answer_question":',
                ),
                line=flow.line,
                column=flow.column,
            )
        _validate_required_fields(flow)
        if flow.output_type and not _type_valid(flow.output_type, record_names):
            raise Namel3ssError(
                build_guidance_message(
                    what=f'AI flow "{flow.name}" has an invalid output type.',
                    why="Output types must be built-in types, record names, or deterministic unions/generics.",
                    fix="Use text, number, boolean, json, list<type>, map<key, value>, union, or a record name.",
                    example="output is text",
                ),
                line=flow.line,
                column=flow.column,
            )
        _validate_output_fields(flow, record_names=record_names)
        _validate_tests_block(flow)
        _validate_chain_steps(flow, known_flow_names=known_flow_names)
        _validate_model_registry(flow, registry=registry)


def _validate_required_fields(flow: ast.AIFlowDefinition) -> None:
    if flow.kind != "chain":
        if not flow.model:
            raise Namel3ssError(f'AI flow "{flow.name}" is missing a model.', line=flow.line, column=flow.column)
        if not flow.prompt and getattr(flow, "prompt_expr", None) is None:
            raise Namel3ssError(f'AI flow "{flow.name}" is missing a prompt.', line=flow.line, column=flow.column)
    if flow.kind == "rag":
        if not flow.sources:
            raise Namel3ssError(f'AI flow "{flow.name}" is missing sources.', line=flow.line, column=flow.column)
        _validate_entries(flow.sources, label="sources", flow=flow)
    if flow.kind == "classification":
        if not flow.labels:
            raise Namel3ssError(f'AI flow "{flow.name}" is missing labels.', line=flow.line, column=flow.column)
        _validate_entries(flow.labels, label="labels", flow=flow)
    if flow.kind == "translate":
        if not flow.source_language:
            raise Namel3ssError(f'Translate flow "{flow.name}" is missing source_language.', line=flow.line, column=flow.column)
        if not flow.target_language:
            raise Namel3ssError(f'Translate flow "{flow.name}" is missing target_language.', line=flow.line, column=flow.column)
    if flow.kind == "qa":
        names = {field.name for field in flow.output_fields or []}
        if "ans" not in names:
            raise Namel3ssError(f'QA flow "{flow.name}" output must include ans.', line=flow.line, column=flow.column)
    if flow.kind == "cot":
        names = {field.name for field in flow.output_fields or []}
        missing = [name for name in ("reasoning", "ans") if name not in names]
        if missing:
            raise Namel3ssError(
                f'COT flow "{flow.name}" output is missing {", ".join(missing)}.',
                line=flow.line,
                column=flow.column,
            )
    if flow.kind == "chain":
        if not flow.chain_steps:
            raise Namel3ssError(f'Chain flow "{flow.name}" is missing steps.', line=flow.line, column=flow.column)
        if not flow.output_fields:
            raise Namel3ssError(f'Chain flow "{flow.name}" is missing output fields.', line=flow.line, column=flow.column)


def _validate_output_fields(flow: ast.AIFlowDefinition, *, record_names: set[str]) -> None:
    fields = flow.output_fields or []
    seen: set[str] = set()
    for field in fields:
        if field.name in seen:
            raise Namel3ssError(
                f'AI flow "{flow.name}" output field "{field.name}" is duplicated.',
                line=field.line or flow.line,
                column=field.column or flow.column,
            )
        seen.add(field.name)
        if not _type_valid(field.type_name, record_names):
            raise Namel3ssError(
                f'AI flow "{flow.name}" output field "{field.name}" has invalid type "{field.type_name}".',
                line=field.line or flow.line,
                column=field.column or flow.column,
            )


def _validate_tests_block(flow: ast.AIFlowDefinition) -> None:
    tests = flow.tests
    if tests is None:
        return
    if not isinstance(tests.dataset, str) or not tests.dataset.strip():
        raise Namel3ssError(f'AI flow "{flow.name}" has an empty tests dataset.', line=flow.line, column=flow.column)
    if not tests.metrics:
        raise Namel3ssError(f'AI flow "{flow.name}" has no tests metrics.', line=flow.line, column=flow.column)
    seen: set[str] = set()
    for metric in tests.metrics:
        normalized = str(metric or "").strip().lower()
        if not normalized:
            raise Namel3ssError(f'AI flow "{flow.name}" has an empty metric name.', line=flow.line, column=flow.column)
        if normalized in seen:
            raise Namel3ssError(f'AI flow "{flow.name}" has duplicate metric "{normalized}".', line=flow.line, column=flow.column)
        seen.add(normalized)
        if normalized not in _ALLOWED_TEST_METRICS:
            raise Namel3ssError(
                build_guidance_message(
                    what=f'AI flow "{flow.name}" has unsupported metric "{normalized}".',
                    why="Only deterministic built-in metrics are allowed.",
                    fix="Use accuracy, precision, recall, f1, f1_score, rouge, bleu, or exact_match.",
                    example='metrics:\n  - accuracy\n  - exact_match',
                ),
                line=flow.line,
                column=flow.column,
            )


def _validate_chain_steps(flow: ast.AIFlowDefinition, *, known_flow_names: set[str] | None) -> None:
    if flow.kind != "chain":
        return
    if not known_flow_names:
        return
    allowed = set(known_flow_names)
    for step in flow.chain_steps or []:
        if step.flow_name not in allowed:
            raise Namel3ssError(
                build_guidance_message(
                    what=f'Chain flow "{flow.name}" calls unknown flow "{step.flow_name}".',
                    why="Chain steps can only call declared flows and patterns.",
                    fix="Define the called flow first or update the step name.",
                    example=f'chain "{flow.name}":\n  steps:\n    - call summarise "{step.flow_name}" with input.text',
                ),
                line=step.line or flow.line,
                column=step.column or flow.column,
            )


def _validate_model_registry(flow: ast.AIFlowDefinition, *, registry) -> None:
    if flow.kind == "chain":
        return
    if not registry.has_entries():
        return
    model_name = str(flow.model or "").strip()
    if not model_name:
        return
    entry = registry.find(model_name)
    if entry is None:
        raise Namel3ssError(
            build_guidance_message(
                what=f'AI flow "{flow.name}" references unknown model "{model_name}".',
                why="The model is not in models_registry.yaml.",
                fix="Register the model with n3 models add.",
                example=f"n3 models add {model_name} 1.0 --provider openai --domain general --tokens-per-second 10 --cost-per-token 0.00001 --privacy-level standard",
            ),
            line=flow.line,
            column=flow.column,
        )
    if entry.status == "deprecated":
        raise Namel3ssError(
            build_guidance_message(
                what=f'AI flow "{flow.name}" uses deprecated model "{entry.ref()}".',
                why="Deprecated models are blocked for new runs.",
                fix="Switch to an active model version.",
                example=f'model is "{entry.name}"',
            ),
            line=flow.line,
            column=flow.column,
        )


def _validate_entries(values: list[str], *, label: str, flow: ast.AIFlowDefinition) -> None:
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise Namel3ssError(
                build_guidance_message(
                    what=f'AI flow "{flow.name}" has an empty {label} entry.',
                    why=f"{label.title()} entries must be simple names.",
                    fix=f"Remove empty entries from {label}.",
                    example=f"{label}:\n  example",
                ),
                line=flow.line,
                column=flow.column,
            )


def _type_valid(type_name: str, record_names: set[str]) -> bool:
    if not isinstance(type_name, str) or not type_name.strip():
        return False
    normalized = type_name.strip()
    if "|" in normalized:
        parts = [part.strip() for part in normalized.split("|")]
        return all(_type_valid(part, record_names) for part in parts if part)
    list_inner = _split_generic(normalized, "list")
    if list_inner is not None:
        return _type_valid(list_inner, record_names)
    map_inner = _split_generic(normalized, "map")
    if map_inner is not None:
        left, right = map_inner
        return _type_valid(left, record_names) and _type_valid(right, record_names)
    if normalized in _ALLOWED_TYPES:
        return True
    return normalized in record_names


def _split_generic(type_name: str, base: str) -> str | tuple[str, str] | None:
    prefix = f"{base}<"
    if not type_name.startswith(prefix) or not type_name.endswith(">"):
        return None
    inner = type_name[len(prefix) : -1].strip()
    if not inner:
        return None
    if base == "list":
        return inner
    parts = _split_top_level(inner, ",")
    if len(parts) != 2:
        return None
    return parts[0].strip(), parts[1].strip()


def _split_top_level(value: str, sep: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    start = 0
    for idx, ch in enumerate(value):
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth = max(0, depth - 1)
        elif ch == sep and depth == 0:
            parts.append(value[start:idx])
            start = idx + 1
    parts.append(value[start:])
    return parts


__all__ = ["validate_ai_flows"]
