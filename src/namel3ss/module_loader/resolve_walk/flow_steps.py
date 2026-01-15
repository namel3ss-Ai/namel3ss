from __future__ import annotations

from typing import Dict, List

from namel3ss.ast import nodes as ast
from namel3ss.module_loader.resolve_names import resolve_name
from namel3ss.module_loader.resolve_walk.expressions import resolve_expression
from namel3ss.module_loader.types import ModuleExports


def resolve_flow_steps(
    steps: List[ast.FlowStep],
    *,
    module_name: str | None,
    alias_map: Dict[str, str],
    local_defs: Dict[str, set[str]],
    exports_map: Dict[str, ModuleExports],
    context_label: str,
) -> None:
    def _resolve_expr(expr: ast.Expression) -> None:
        resolve_expression(
            expr,
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
        )

    for step in steps:
        if isinstance(step, ast.FlowCreate):
            step.record_name = resolve_name(
                step.record_name,
                kind="record",
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
                line=step.line,
                column=step.column,
            )
            for field in step.fields:
                _resolve_expr(field.value)
            continue
        if isinstance(step, ast.FlowUpdate):
            step.record_name = resolve_name(
                step.record_name,
                kind="record",
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
                line=step.line,
                column=step.column,
            )
            for update in step.updates:
                _resolve_expr(update.value)
            continue
        if isinstance(step, ast.FlowDelete):
            step.record_name = resolve_name(
                step.record_name,
                kind="record",
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
                line=step.line,
                column=step.column,
            )
            continue
        if isinstance(step, (ast.FlowInput, ast.FlowRequire)):
            continue


__all__ = ["resolve_flow_steps"]
