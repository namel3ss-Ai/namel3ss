from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.lang.keywords import is_keyword
from namel3ss.schema.records import RecordSchema
from namel3ss.validation import ValidationMode

from namel3ss.flow_contract.steps import parse_selector_expression, validate_declarative_flow


def validate_flow_names(flows: list[ir.Flow]) -> set[str]:
    seen: dict[str, ir.Flow] = {}
    for flow in flows:
        name = flow.name
        if is_keyword(name):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Flow name '{name}' is reserved.",
                    why="Reserved words have fixed meaning in the language.",
                    fix="Rename the flow to a non-reserved name.",
                    example=f'flow "{name}_flow":',
                ),
                line=flow.line,
                column=flow.column,
            )
        if name in seen:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Duplicate flow name '{name}'.",
                    why="Flow names must be unique.",
                    fix="Rename one of the flows so each name is unique.",
                    example=f'flow "{name}_v2":',
                ),
                line=flow.line,
                column=flow.column,
            )
        seen[name] = flow
    return set(seen.keys())


def validate_declarative_flows(
    flows: list[ir.Flow],
    record_map: dict[str, RecordSchema],
    tools: dict[str, ir.ToolDecl] | None = None,
    *,
    mode: ValidationMode = ValidationMode.RUNTIME,
    warnings: list | None = None,
) -> None:
    tool_map = tools or {}
    for flow in flows:
        if not getattr(flow, "declarative", False):
            continue
        validate_declarative_flow(flow, record_map, tool_map, mode=mode, warnings=warnings)


__all__ = ["parse_selector_expression", "validate_declarative_flows", "validate_flow_names"]
