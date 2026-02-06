from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.parser.sugar.lowering.expressions import _lower_expression


def lower_ai_flow(flow: ast.AIFlowDefinition) -> ast.AIFlowDefinition:
    output_type = flow.output_type
    if output_type is None and flow.output_fields is None and flow.kind != "chain":
        output_type = "text"
    output_fields = None
    if flow.output_fields:
        output_fields = [
            ast.AIOutputField(
                name=field.name,
                type_name=field.type_name,
                line=field.line,
                column=field.column,
            )
            for field in flow.output_fields
        ]
    chain_steps = None
    if flow.chain_steps:
        chain_steps = [
            ast.ChainStep(
                flow_kind=step.flow_kind,
                flow_name=step.flow_name,
                input_expr=_lower_expression(step.input_expr),
                line=step.line,
                column=step.column,
            )
            for step in flow.chain_steps
        ]
    tests = None
    if flow.tests:
        tests = ast.AIFlowTestConfig(
            dataset=flow.tests.dataset,
            metrics=list(flow.tests.metrics),
            line=flow.tests.line,
            column=flow.tests.column,
        )
    return ast.AIFlowDefinition(
        name=flow.name,
        kind=flow.kind,
        model=flow.model,
        prompt=flow.prompt,
        prompt_expr=_lower_expression(flow.prompt_expr) if flow.prompt_expr else None,
        dataset=flow.dataset,
        output_type=output_type,
        source_language=flow.source_language,
        target_language=flow.target_language,
        output_fields=output_fields,
        labels=list(flow.labels) if flow.labels else None,
        sources=list(flow.sources) if flow.sources else None,
        chain_steps=chain_steps,
        tests=tests,
        return_expr=_lower_expression(flow.return_expr) if flow.return_expr else None,
        line=flow.line,
        column=flow.column,
    )


def ai_flow_to_flow(flow: ast.AIFlowDefinition) -> ast.Flow:
    ai_metadata = ast.AIFlowMetadata(
        model=flow.model,
        prompt=flow.prompt,
        prompt_expr=flow.prompt_expr,
        dataset=flow.dataset,
        kind=flow.kind,
        output_type=flow.output_type,
        source_language=flow.source_language,
        target_language=flow.target_language,
        output_fields=list(flow.output_fields) if flow.output_fields else None,
        labels=list(flow.labels) if flow.labels else None,
        sources=list(flow.sources) if flow.sources else None,
        chain_steps=list(flow.chain_steps) if flow.chain_steps else None,
        tests=flow.tests,
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
