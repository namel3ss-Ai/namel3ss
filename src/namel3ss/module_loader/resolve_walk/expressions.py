from __future__ import annotations

from typing import Dict

from namel3ss.ast import nodes as ast
from namel3ss.module_loader.resolve_names import resolve_name
from namel3ss.module_loader.types import ModuleExports


def resolve_expression(
    expr: ast.Expression,
    *,
    module_name: str | None,
    alias_map: Dict[str, str],
    local_defs: Dict[str, set[str]],
    exports_map: Dict[str, ModuleExports],
    context_label: str,
) -> None:
    if isinstance(expr, ast.CallFunctionExpr):
        expr.function_name = resolve_name(
            expr.function_name,
            kind="function",
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
            line=expr.line,
            column=expr.column,
        )
        for arg in expr.arguments:
            resolve_expression(
                arg.value,
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
            )
        return
    if isinstance(expr, ast.UnaryOp):
        resolve_expression(
            expr.operand,
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
        )
        return
    if isinstance(expr, ast.BinaryOp):
        resolve_expression(
            expr.left,
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
        )
        resolve_expression(
            expr.right,
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
        )
        return
    if isinstance(expr, ast.Comparison):
        resolve_expression(
            expr.left,
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
        )
        resolve_expression(
            expr.right,
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
        )
        return
    if isinstance(expr, ast.ToolCallExpr):
        expr.tool_name = resolve_name(
            expr.tool_name,
            kind="tool",
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
            line=expr.line,
            column=expr.column,
        )
        for arg in expr.arguments:
            resolve_expression(
                arg.value,
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
            )
        return
    if isinstance(expr, ast.ListExpr):
        for item in expr.items:
            resolve_expression(
                item,
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
            )
        return
    if isinstance(expr, ast.MapExpr):
        for entry in expr.entries:
            resolve_expression(
                entry.key,
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
            )
            resolve_expression(
                entry.value,
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
            )
        return
    if isinstance(expr, ast.ListOpExpr):
        resolve_expression(
            expr.target,
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
        )
        if expr.value is not None:
            resolve_expression(
                expr.value,
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
            )
        if expr.index is not None:
            resolve_expression(
                expr.index,
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
            )
        return
    if isinstance(expr, ast.ListMapExpr):
        resolve_expression(
            expr.target,
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
        )
        resolve_expression(
            expr.body,
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
        )
        return
    if isinstance(expr, ast.ListFilterExpr):
        resolve_expression(
            expr.target,
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
        )
        resolve_expression(
            expr.predicate,
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
        )
        return
    if isinstance(expr, ast.ListReduceExpr):
        resolve_expression(
            expr.target,
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
        )
        resolve_expression(
            expr.start,
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
        )
        resolve_expression(
            expr.body,
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
        )
        return
    if isinstance(expr, ast.MapOpExpr):
        resolve_expression(
            expr.target,
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
        )
        if expr.key is not None:
            resolve_expression(
                expr.key,
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
            )
        if expr.value is not None:
            resolve_expression(
                expr.value,
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
            )
        return


__all__ = ["resolve_expression"]
