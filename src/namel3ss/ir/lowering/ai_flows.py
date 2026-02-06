from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.ir.lowering.expressions import _lower_expression
from namel3ss.ir.model.ai_flows import AIFlowDefinition, AIFlowTestConfig, AIOutputField, ChainStep


def lower_ai_flows(ai_flows: list[ast.AIFlowDefinition]) -> list[AIFlowDefinition]:
    lowered: list[AIFlowDefinition] = []
    for flow in ai_flows:
        output_fields = None
        if flow.output_fields:
            output_fields = [
                AIOutputField(
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
                ChainStep(
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
            tests = AIFlowTestConfig(
                dataset=flow.tests.dataset,
                metrics=list(flow.tests.metrics),
                line=flow.tests.line,
                column=flow.tests.column,
            )
        lowered.append(
            AIFlowDefinition(
                name=flow.name,
                kind=flow.kind,
                model=flow.model,
                prompt=flow.prompt,
                prompt_expr=_lower_expression(flow.prompt_expr) if flow.prompt_expr else None,
                dataset=flow.dataset,
                output_type=flow.output_type,
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
        )
    return lowered


__all__ = ["lower_ai_flows"]
