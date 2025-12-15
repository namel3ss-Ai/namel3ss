from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.ir.lowering.statements import _lower_statement
from namel3ss.ir.model.agents import AgentDecl
from namel3ss.ir.model.program import Flow


def lower_flow(flow: ast.Flow, agents: dict[str, AgentDecl]) -> Flow:
    return Flow(
        name=flow.name,
        body=[_lower_statement(stmt, agents) for stmt in flow.body],
        line=flow.line,
        column=flow.column,
    )
