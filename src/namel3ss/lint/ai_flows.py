from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.lint.types import Finding


_ALLOWED_TYPES = {"text", "number", "boolean", "json"}
_AI_FLOW_KINDS = {"llm_call", "rag", "classification", "summarise", "translate", "qa", "cot", "chain"}
_ALLOWED_TEST_METRICS = {"accuracy", "precision", "recall", "f1", "f1_score", "rouge", "bleu", "exact_match"}


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
        if flow.kind != "chain" and not flow.model:
            findings.append(
                Finding(
                    code="ai_flows.missing_model",
                    message=f'AI flow "{flow.name}" is missing a model.',
                    line=flow.line,
                    column=flow.column,
                    severity="error",
                )
            )
        if not flow.prompt and getattr(flow, "prompt_expr", None) is None and flow.kind != "chain":
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
        if flow.kind == "translate":
            if not getattr(flow, "source_language", None):
                findings.append(
                    Finding(
                        code="ai_flows.missing_source_language",
                        message=f'Translate flow "{flow.name}" is missing source_language.',
                        line=flow.line,
                        column=flow.column,
                        severity="error",
                    )
                )
            if not getattr(flow, "target_language", None):
                findings.append(
                    Finding(
                        code="ai_flows.missing_target_language",
                        message=f'Translate flow "{flow.name}" is missing target_language.',
                        line=flow.line,
                        column=flow.column,
                        severity="error",
                    )
                )
        output_fields = list(getattr(flow, "output_fields", []) or [])
        if flow.kind == "qa":
            if "ans" not in {field.name for field in output_fields}:
                findings.append(
                    Finding(
                        code="ai_flows.qa_missing_ans",
                        message=f'QA flow "{flow.name}" output must include ans.',
                        line=flow.line,
                        column=flow.column,
                        severity="error",
                    )
                )
        if flow.kind == "cot":
            names = {field.name for field in output_fields}
            for required in ("reasoning", "ans"):
                if required not in names:
                    findings.append(
                        Finding(
                            code="ai_flows.cot_missing_output",
                            message=f'COT flow "{flow.name}" output must include {required}.',
                            line=flow.line,
                            column=flow.column,
                            severity="error",
                        )
                    )
        if flow.kind == "chain":
            if not getattr(flow, "chain_steps", None):
                findings.append(
                    Finding(
                        code="ai_flows.chain_missing_steps",
                        message=f'Chain flow "{flow.name}" is missing steps.',
                        line=flow.line,
                        column=flow.column,
                        severity="error",
                    )
                )
            if not output_fields:
                findings.append(
                    Finding(
                        code="ai_flows.chain_missing_output",
                        message=f'Chain flow "{flow.name}" is missing output fields.',
                        line=flow.line,
                        column=flow.column,
                        severity="error",
                    )
                )
        for field in output_fields:
            if not _type_valid(field.type_name, record_names):
                findings.append(
                    Finding(
                        code="ai_flows.invalid_output_field",
                        message=f'AI flow "{flow.name}" output field "{field.name}" has invalid type.',
                        line=field.line or flow.line,
                        column=field.column or flow.column,
                        severity=severity,
                    )
                )
        tests = getattr(flow, "tests", None)
        if tests is not None:
            metrics = list(getattr(tests, "metrics", []) or [])
            if not metrics:
                findings.append(
                    Finding(
                        code="ai_flows.tests_missing_metrics",
                        message=f'AI flow "{flow.name}" tests block has no metrics.',
                        line=flow.line,
                        column=flow.column,
                        severity="error",
                    )
                )
            for metric in metrics:
                normalized = str(metric or "").strip().lower()
                if normalized not in _ALLOWED_TEST_METRICS:
                    findings.append(
                        Finding(
                            code="ai_flows.invalid_metric",
                            message=f'AI flow "{flow.name}" has unsupported metric "{metric}".',
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
    if "|" in type_name:
        parts = [part.strip() for part in type_name.split("|")]
        return all(_type_valid(part, record_names) for part in parts if part)
    map_inner = _split_map_type(type_name)
    if map_inner is not None:
        return _type_valid(map_inner[0], record_names) and _type_valid(map_inner[1], record_names)
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


def _split_map_type(type_name: str) -> tuple[str, str] | None:
    if not type_name.startswith("map<") or not type_name.endswith(">"):
        return None
    inner = type_name[4:-1]
    depth = 0
    split = -1
    for idx, ch in enumerate(inner):
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            split = idx
            break
    if split <= 0:
        return None
    left = inner[:split].strip()
    right = inner[split + 1 :].strip()
    if not left or not right:
        return None
    return left, right


__all__ = ["lint_ai_flows"]
