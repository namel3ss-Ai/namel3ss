from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.parser.sugar.lowering.expressions import _lower_expression


def lower_ai_flow(flow: ast.AIFlowDefinition) -> ast.AIFlowDefinition:
    output_type = flow.output_type or "text"
    return ast.AIFlowDefinition(
        name=flow.name,
        kind=flow.kind,
        model=flow.model,
        prompt=flow.prompt,
        dataset=flow.dataset,
        output_type=output_type,
        labels=list(flow.labels) if flow.labels else None,
        sources=list(flow.sources) if flow.sources else None,
        return_expr=_lower_expression(flow.return_expr) if flow.return_expr else None,
        line=flow.line,
        column=flow.column,
    )


def ai_flow_to_flow(flow: ast.AIFlowDefinition) -> ast.Flow:
    ai_metadata = ast.AIFlowMetadata(
        model=flow.model,
        prompt=flow.prompt,
        dataset=flow.dataset,
        kind=flow.kind,
        output_type=flow.output_type,
        labels=list(flow.labels) if flow.labels else None,
        sources=list(flow.sources) if flow.sources else None,
        line=flow.line,
        column=flow.column,
    )
    body: list[ast.Statement] = []
    if flow.return_expr is not None:
        body.append(ast.Return(expression=flow.return_expr, line=flow.line, column=flow.column))
    return ast.Flow(
        name=flow.name,
        body=body,
        requires=None,
        audited=False,
        purity=getattr(flow, "purity", "effectful"),
        steps=None,
        declarative=False,
        ai_metadata=ai_metadata,
        line=flow.line,
        column=flow.column,
    )


__all__ = ["ai_flow_to_flow", "lower_ai_flow"]
