from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


_AI_FLOW_KINDS = {"llm_call", "rag", "classification", "summarise"}
_ALLOWED_TYPES = {"text", "number", "boolean", "json"}


def validate_ai_flows(ai_flows: list[ast.AIFlowDefinition], *, record_names: set[str]) -> None:
    seen: set[str] = set()
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
                    fix="Use llm_call, rag, classification, or summarise.",
                    example='llm_call "summarise":',
                ),
                line=flow.line,
                column=flow.column,
            )
        if not flow.model:
            raise Namel3ssError(f'AI flow "{flow.name}" is missing a model.', line=flow.line, column=flow.column)
        if not flow.prompt:
            raise Namel3ssError(f'AI flow "{flow.name}" is missing a prompt.', line=flow.line, column=flow.column)
        if flow.kind == "rag":
            if not flow.sources:
                raise Namel3ssError(
                    f'AI flow "{flow.name}" is missing sources.',
                    line=flow.line,
                    column=flow.column,
                )
            _validate_entries(flow.sources, label="sources", flow=flow)
        if flow.kind == "classification":
            if not flow.labels:
                raise Namel3ssError(
                    f'AI flow "{flow.name}" is missing labels.',
                    line=flow.line,
                    column=flow.column,
                )
            _validate_entries(flow.labels, label="labels", flow=flow)
        if not flow.output_type:
            flow.output_type = "text"
        if not _type_valid(flow.output_type, record_names):
            raise Namel3ssError(
                build_guidance_message(
                    what=f'AI flow "{flow.name}" has an invalid output type.',
                    why="Output types must be built-in types or record names.",
                    fix="Use text, number, boolean, json, list<type>, or a record name.",
                    example="output is text",
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
    if not isinstance(type_name, str) or not type_name:
        return False
    inner = _split_list_type(type_name)
    if inner is not None:
        return _type_valid(inner, record_names)
    if type_name in _ALLOWED_TYPES:
        return True
    return type_name in record_names


def _split_list_type(type_name: str) -> str | None:
    if not type_name.startswith("list<"):
        return None
    depth = 0
    start = None
    end = None
    for idx, ch in enumerate(type_name):
        if ch == "<":
            depth += 1
            if depth == 1:
                start = idx + 1
        elif ch == ">":
            depth -= 1
            if depth == 0:
                end = idx
                break
    if start is None or end is None or end != len(type_name) - 1:
        return None
    inner = type_name[start:end].strip()
    if not inner:
        return None
    return inner


__all__ = ["validate_ai_flows"]
