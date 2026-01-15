from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.ir.lowering.statements import _lower_statement
from namel3ss.ir.lowering.flow_steps import lower_flow_steps
from namel3ss.ir.lowering.expressions import _lower_expression
from namel3ss.ir.model.agents import AgentDecl
from namel3ss.ir.model.program import Flow
from namel3ss.ir.lowering.agents import validate_agent_statement


def lower_flow(flow: ast.Flow, agents: dict[str, AgentDecl]) -> Flow:
    declarative = bool(getattr(flow, "declarative", False)) or bool(getattr(flow, "steps", None))
    ir_body = []
    if not declarative:
        for stmt in flow.body:
            lowered = _lower_statement(stmt, agents)
            validate_agent_statement(lowered, agents)
            ir_body.append(lowered)
    return Flow(
        name=flow.name,
        body=ir_body,
        requires=_lower_expression(flow.requires) if flow.requires else None,
        audited=bool(flow.audited),
        steps=lower_flow_steps(getattr(flow, "steps", None)),
        declarative=declarative,
        line=flow.line,
        column=flow.column,
    )
