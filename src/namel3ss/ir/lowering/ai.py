from __future__ import annotations

from typing import Dict, List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.model.ai import AIDecl, AIMemory
from namel3ss.ir.model.tools import ToolDecl
from namel3ss.runtime.ai.providers.registry import is_supported_provider


def _lower_ai_decls(ais: List[ast.AIDecl], tools: Dict[str, ToolDecl]) -> Dict[str, AIDecl]:
    ai_map: Dict[str, AIDecl] = {}
    for ai in ais:
        if ai.name in ai_map:
            raise Namel3ssError(f"Duplicate AI declaration '{ai.name}'", line=ai.line, column=ai.column)
        if not ai.model:
            raise Namel3ssError(f"AI '{ai.name}' must specify a model", line=ai.line, column=ai.column)
        provider = (ai.provider or "mock").lower()
        if not is_supported_provider(provider):
            raise Namel3ssError(f"Unknown AI provider '{provider}'", line=ai.line, column=ai.column)
        exposed: List[str] = []
        for tool in ai.exposed_tools:
            if tool not in tools:
                raise Namel3ssError(f"AI '{ai.name}' exposes unknown tool '{tool}'", line=ai.line, column=ai.column)
            if tool in exposed:
                raise Namel3ssError(f"Duplicate tool exposure '{tool}' in AI '{ai.name}'", line=ai.line, column=ai.column)
            exposed.append(tool)
        ai_map[ai.name] = AIDecl(
            name=ai.name,
            model=ai.model,
            provider=provider,
            system_prompt=ai.system_prompt,
            exposed_tools=exposed,
            memory=AIMemory(
                short_term=ai.memory.short_term,
                semantic=ai.memory.semantic,
                profile=ai.memory.profile,
                line=ai.memory.line,
                column=ai.memory.column,
            ),
            line=ai.line,
            column=ai.column,
        )
    return ai_map
