from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.lint.types import Finding


_ALLOWED_TYPES = {"text", "number", "boolean", "json"}
_AI_FLOW_KINDS = {"llm_call", "rag", "classification", "summarise"}


def lint_ai_flows(ast_program, *, strict: bool, record_names: set[str] | None = None) -> list[Finding]:
    ai_flows = list(getattr(ast_program, "ai_flows", []) or [])
    if not ai_flows:
        return []
    if record_names is None:
        record_names = {record.name for record in getattr(ast_program, "records", [])}
    severity = "error" if strict else "warning"
    findings: list[Finding] = []
    seen: set[str] = set()
    for flow in ai_flows:
        if flow.name in seen:
            findings.append(
                Finding(
                    code="ai_flows.duplicate",
                    message=f'AI flow "{flow.name}" is declared more than once.',
                    line=flow.line,
                    column=flow.column,
                    severity="error",
                )
            )
        seen.add(flow.name)
        if flow.kind not in _AI_FLOW_KINDS:
            findings.append(
                Finding(
                    code="ai_flows.invalid_kind",
                    message=f'AI flow "{flow.name}" uses an unsupported type.',
                    line=flow.line,
                    column=flow.column,
                    severity="error",
                )
            )
        if not flow.model:
            findings.append(
                Finding(
                    code="ai_flows.missing_model",
                    message=f'AI flow "{flow.name}" is missing a model.',
                    line=flow.line,
                    column=flow.column,
                    severity="error",
                )
            )
        if not flow.prompt:
            findings.append(
                Finding(
                    code="ai_flows.missing_prompt",
                    message=f'AI flow "{flow.name}" is missing a prompt.',
                    line=flow.line,
                    column=flow.column,
                    severity="error",
                )
            )
        if flow.kind == "rag" and not flow.sources:
            findings.append(
                Finding(
                    code="ai_flows.missing_sources",
                    message=f'AI flow "{flow.name}" is missing sources.',
                    line=flow.line,
                    column=flow.column,
                    severity="error",
                )
            )
        if flow.kind == "classification" and not flow.labels:
            findings.append(
                Finding(
                    code="ai_flows.missing_labels",
                    message=f'AI flow "{flow.name}" is missing labels.',
                    line=flow.line,
                    column=flow.column,
                    severity="error",
                )
            )
        if flow.output_type and not _type_valid(flow.output_type, record_names):
            findings.append(
                Finding(
                    code="ai_flows.invalid_output",
                    message=f'AI flow "{flow.name}" has an invalid output type.',
                    line=flow.line,
                    column=flow.column,
                    severity=severity,
                )
            )
    return findings


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


__all__ = ["lint_ai_flows"]
