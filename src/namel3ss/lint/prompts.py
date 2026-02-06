from __future__ import annotations

import re

from namel3ss.ast import nodes as ast
from namel3ss.lang.keywords import is_keyword
from namel3ss.lint.types import Finding


_PROMPT_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PROMPT_REF_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\\.[A-Za-z_][A-Za-z0-9_]*)*$")
_SEMVER_RE = re.compile(r"^\\d+\\.\\d+(?:\\.\\d+)?$")


def lint_prompts(ast_program, *, strict: bool) -> list[Finding]:
    prompts = list(getattr(ast_program, "prompts", []) or [])
    if not prompts and not _has_prompt_references(ast_program):
        return []
    severity = "error" if strict else "warning"
    findings: list[Finding] = []
    prompt_names: set[str] = set()
    for prompt in prompts:
        name = prompt.name
        if not _PROMPT_NAME_RE.match(str(name or "")) or is_keyword(str(name)):
            findings.append(
                Finding(
                    code="prompts.invalid_name",
                    message=f'Prompt name "{name}" is not valid.',
                    line=prompt.line,
                    column=prompt.column,
                    severity="error",
                )
            )
            continue
        if name in prompt_names:
            findings.append(
                Finding(
                    code="prompts.duplicate",
                    message=f'Prompt "{name}" is declared more than once.',
                    line=prompt.line,
                    column=prompt.column,
                    severity="error",
                )
            )
        prompt_names.add(name)
        if not isinstance(prompt.version, str) or not _SEMVER_RE.match(prompt.version.strip()):
            findings.append(
                Finding(
                    code="prompts.invalid_version",
                    message=f'Prompt "{name}" has an invalid version.',
                    line=prompt.line,
                    column=prompt.column,
                    severity="error",
                )
            )
        if not isinstance(prompt.text, str) or not prompt.text.strip():
            findings.append(
                Finding(
                    code="prompts.missing_text",
                    message=f'Prompt "{name}" is missing text.',
                    line=prompt.line,
                    column=prompt.column,
                    severity="error",
                )
            )
    findings.extend(_lint_prompt_references(ast_program, prompt_names, severity=severity))
    return findings


def _lint_prompt_references(ast_program, prompt_names: set[str], *, severity: str) -> list[Finding]:
    findings: list[Finding] = []
    for flow in getattr(ast_program, "flows", []) or []:
        metadata = getattr(flow, "ai_metadata", None)
        if metadata is None:
            continue
        prompt_value = getattr(metadata, "prompt", None)
        if _is_prompt_reference(prompt_value) and prompt_value not in prompt_names:
            findings.append(
                Finding(
                    code="prompts.unknown_reference",
                    message=f'Prompt "{prompt_value}" is not defined.',
                    line=metadata.line or flow.line,
                    column=metadata.column or flow.column,
                    severity=severity,
                )
            )
    for ai_flow in getattr(ast_program, "ai_flows", []) or []:
        if getattr(ai_flow, "prompt_expr", None) is not None:
            continue
        prompt_value = getattr(ai_flow, "prompt", None)
        if _is_prompt_reference(prompt_value) and prompt_value not in prompt_names:
            findings.append(
                Finding(
                    code="prompts.unknown_reference",
                    message=f'Prompt "{prompt_value}" is not defined.',
                    line=ai_flow.line,
                    column=ai_flow.column,
                    severity=severity,
                )
            )
    return findings


def _has_prompt_references(ast_program) -> bool:
    for flow in getattr(ast_program, "flows", []) or []:
        metadata = getattr(flow, "ai_metadata", None)
        if metadata is not None and _is_prompt_reference(getattr(metadata, "prompt", None)):
            return True
    for ai_flow in getattr(ast_program, "ai_flows", []) or []:
        if getattr(ai_flow, "prompt_expr", None) is not None:
            continue
        if _is_prompt_reference(getattr(ai_flow, "prompt", None)):
            return True
    return False


def _is_prompt_reference(value: object) -> bool:
    if not isinstance(value, str):
        return False
    return bool(_PROMPT_REF_RE.match(value))


__all__ = ["lint_prompts"]
