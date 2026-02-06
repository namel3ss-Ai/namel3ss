from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.ir.lowering.statements import _lower_statement
from namel3ss.ir.lowering.flow_steps import lower_flow_steps
from namel3ss.ir.lowering.expressions import _lower_expression
from namel3ss.ir.model.agents import AgentDecl
from namel3ss.ir.model.program import Flow
from namel3ss.ir.model.ai import AIFlowMetadata
from namel3ss.ir.model.ai_flows import AIFlowTestConfig, AIOutputField, ChainStep
from namel3ss.ir.lowering.agents import validate_agent_statement


def lower_flow(flow: ast.Flow, agents: dict[str, AgentDecl]) -> Flow:
    declarative = bool(getattr(flow, "declarative", False)) or bool(getattr(flow, "steps", None))
    ir_body = []
    if not declarative:
        for stmt in flow.body:
            lowered = _lower_statement(stmt, agents)
            validate_agent_statement(lowered, agents)
            ir_body.append(lowered)
    ai_meta = _lower_ai_metadata(getattr(flow, "ai_metadata", None))
    return Flow(
        name=flow.name,
        body=ir_body,
        requires=_lower_expression(flow.requires) if flow.requires else None,
        audited=bool(flow.audited),
        purity=getattr(flow, "purity", "effectful"),
        steps=lower_flow_steps(getattr(flow, "steps", None)),
        declarative=declarative,
        ai_metadata=ai_meta,
        line=flow.line,
        column=flow.column,
    )


def _lower_ai_metadata(metadata: ast.AIFlowMetadata | None) -> AIFlowMetadata | None:
    if metadata is None:
        return None
    output_fields = None
    if metadata.output_fields:
        output_fields = [
            AIOutputField(
                name=field.name,
                type_name=field.type_name,
                line=field.line,
                column=field.column,
            )
            for field in metadata.output_fields
        ]
    chain_steps = None
    if metadata.chain_steps:
        chain_steps = [
            ChainStep(
                flow_kind=step.flow_kind,
                flow_name=step.flow_name,
                input_expr=_lower_expression(step.input_expr),
                line=step.line,
                column=step.column,
            )
            for step in metadata.chain_steps
        ]
    tests = None
    if metadata.tests:
        tests = AIFlowTestConfig(
            dataset=metadata.tests.dataset,
            metrics=list(metadata.tests.metrics),
            line=metadata.tests.line,
            column=metadata.tests.column,
        )
    return AIFlowMetadata(
        model=metadata.model,
        prompt=metadata.prompt,
        prompt_expr=_lower_expression(metadata.prompt_expr) if metadata.prompt_expr else None,
        dataset=metadata.dataset,
        kind=getattr(metadata, "kind", None),
        output_type=getattr(metadata, "output_type", None),
        source_language=getattr(metadata, "source_language", None),
        target_language=getattr(metadata, "target_language", None),
        output_fields=output_fields,
        labels=list(getattr(metadata, "labels", []) or []) or None,
        sources=list(getattr(metadata, "sources", []) or []) or None,
        chain_steps=chain_steps,
        tests=tests,
        line=metadata.line,
        column=metadata.column,
    )
