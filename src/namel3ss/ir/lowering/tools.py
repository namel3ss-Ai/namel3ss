from __future__ import annotations

from typing import Dict, List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.model.tools import ToolDecl, ToolField


def _lower_tools(tools: List[ast.ToolDecl]) -> Dict[str, ToolDecl]:
    tool_map: Dict[str, ToolDecl] = {}
    for tool in tools:
        if tool.name in tool_map:
            raise Namel3ssError(f"Duplicate tool declaration '{tool.name}'", line=tool.line, column=tool.column)
        tool_map[tool.name] = ToolDecl(
            name=tool.name,
            kind=tool.kind,
            input_fields=[
                ToolField(
                    name=field.name,
                    type_name=field.type_name,
                    required=field.required,
                    line=field.line,
                    column=field.column,
                )
                for field in tool.input_fields
            ],
            output_fields=[
                ToolField(
                    name=field.name,
                    type_name=field.type_name,
                    required=field.required,
                    line=field.line,
                    column=field.column,
                )
                for field in tool.output_fields
            ],
            capabilities=tuple(tool.capabilities or ()),
            purity=tool.purity,
            timeout_seconds=tool.timeout_seconds,
            line=tool.line,
            column=tool.column,
        )
    return tool_map


__all__ = ["_lower_tools"]
