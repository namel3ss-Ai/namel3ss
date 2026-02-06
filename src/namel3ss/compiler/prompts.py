from __future__ import annotations

import re

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.lang.keywords import is_keyword


_PROMPT_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PROMPT_REF_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\\.[A-Za-z_][A-Za-z0-9_]*)*$")
_SEMVER_RE = re.compile(r"^\d+\.\d+(?:\.\d+)?$")


def validate_prompts(prompts: list[ast.PromptDefinition]) -> set[str]:
    seen: dict[str, ast.PromptDefinition] = {}
    for prompt in prompts:
        name = prompt.name
        if not _PROMPT_NAME_RE.match(str(name or "")) or is_keyword(str(name)):
            raise Namel3ssError(
                build_guidance_message(
                    what=f'Prompt name "{name}" is not valid.',
                    why="Prompt names use simple identifiers.",
                    fix="Use letters, numbers, and underscores only.",
                    example='prompt "summary_prompt":',
                ),
                line=prompt.line,
                column=prompt.column,
            )
        if name in seen:
            raise Namel3ssError(
                build_guidance_message(
                    what=f'Prompt "{name}" is declared more than once.',
                    why="Prompt names must be unique.",
                    fix="Rename or remove the duplicate prompt.",
                    example=f'prompt "{name}":',
                ),
                line=prompt.line,
                column=prompt.column,
            )
        if not isinstance(prompt.version, str) or not _SEMVER_RE.match(prompt.version.strip()):
            raise Namel3ssError(
                build_guidance_message(
                    what=f'Prompt "{name}" has an invalid version.',
                    why="Prompt versions must look like 1.0 or 1.0.0.",
                    fix="Use a numeric version with at least two parts.",
                    example='version is "1.0.0"',
                ),
                line=prompt.line,
                column=prompt.column,
            )
        if not isinstance(prompt.text, str) or not prompt.text.strip():
            raise Namel3ssError(
                build_guidance_message(
                    what=f'Prompt "{name}" is missing text.',
                    why="Prompt text must be a non-empty string.",
                    fix="Add a text value to the prompt.",
                    example='text is "Summarise the input."',
                ),
                line=prompt.line,
                column=prompt.column,
            )
        seen[name] = prompt
    return set(seen.keys())


def validate_prompt_references(
    flows: list[ast.Flow],
    ai_flows: list[ast.AIFlowDefinition],
    *,
    prompt_names: set[str],
) -> None:
    for flow in flows:
        metadata = getattr(flow, "ai_metadata", None)
        if metadata is None:
            continue
        _validate_prompt_reference(
            metadata.prompt,
            prompt_names=prompt_names,
            line=metadata.line or flow.line,
            column=metadata.column or flow.column,
        )
    for ai_flow in ai_flows:
        if getattr(ai_flow, "prompt_expr", None) is not None:
            continue
        _validate_prompt_reference(
            ai_flow.prompt,
            prompt_names=prompt_names,
            line=ai_flow.line,
            column=ai_flow.column,
        )


def _validate_prompt_reference(
    value: str,
    *,
    prompt_names: set[str],
    line: int | None,
    column: int | None,
) -> None:
    if not isinstance(value, str):
        return
    if not _PROMPT_REF_RE.match(value):
        return
    if value in prompt_names:
        return
    raise Namel3ssError(
        build_guidance_message(
            what=f'Prompt "{value}" is not defined.',
            why="Prompt references must match a prompt declaration.",
            fix="Add a prompt block with that name or use a longer prompt string.",
            example='prompt "summary_prompt":\n  version is "1.0.0"\n  text is "Summarise the input."',
        ),
        line=line,
        column=column,
    )


__all__ = ["validate_prompt_references", "validate_prompts"]
