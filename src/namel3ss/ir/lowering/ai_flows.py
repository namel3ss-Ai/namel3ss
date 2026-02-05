from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.ir.lowering.expressions import _lower_expression
from namel3ss.ir.model.ai_flows import AIFlowDefinition


def lower_ai_flows(ai_flows: list[ast.AIFlowDefinition]) -> list[AIFlowDefinition]:
    lowered: list[AIFlowDefinition] = []
    for flow in ai_flows:
        lowered.append(
            AIFlowDefinition(
                name=flow.name,
                kind=flow.kind,
                model=flow.model,
                prompt=flow.prompt,
                dataset=flow.dataset,
                output_type=flow.output_type,
                labels=list(flow.labels) if flow.labels else None,
                sources=list(flow.sources) if flow.sources else None,
                return_expr=_lower_expression(flow.return_expr) if flow.return_expr else None,
                line=flow.line,
                column=flow.column,
            )
        )
    return lowered


__all__ = ["lower_ai_flows"]
