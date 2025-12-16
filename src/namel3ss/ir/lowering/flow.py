from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.ir.lowering.statements import _lower_statement
from namel3ss.ir.model.agents import AgentDecl
from namel3ss.ir.model.program import Flow
from namel3ss.ir.lowering.agents import validate_agent_statement


def lower_flow(flow: ast.Flow, agents: dict[str, AgentDecl]) -> Flow:
    ir_body = []
    for stmt in flow.body:
        lowered = _lower_statement(stmt, agents)
        validate_agent_statement(lowered, agents)
        ir_body.append(lowered)
    return Flow(
        name=flow.name,
        body=ir_body,
        line=flow.line,
        column=flow.column,
    )
