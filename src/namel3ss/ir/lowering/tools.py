from __future__ import annotations

from typing import Dict, List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.model.tools import ToolDecl


def _lower_tools(tools: List[ast.ToolDecl]) -> Dict[str, ToolDecl]:
    tool_map: Dict[str, ToolDecl] = {}
    for tool in tools:
        if tool.name in tool_map:
            raise Namel3ssError(f"Duplicate tool declaration '{tool.name}'", line=tool.line, column=tool.column)
        tool_map[tool.name] = ToolDecl(name=tool.name, kind=tool.kind, line=tool.line, column=tool.column)
    return tool_map
