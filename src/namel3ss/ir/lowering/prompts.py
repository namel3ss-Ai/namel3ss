from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.ir.model.prompts import PromptDefinition


def lower_prompts(prompts: list[ast.PromptDefinition]) -> list[PromptDefinition]:
    return [PromptDefinition(
        name=prompt.name,
        version=prompt.version,
        text=prompt.text,
        description=prompt.description,
        line=prompt.line,
        column=prompt.column,
    ) for prompt in prompts]


__all__ = ["lower_prompts"]
