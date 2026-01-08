from __future__ import annotations

from typing import Dict, List

from namel3ss.ast import nodes as ast
from namel3ss.module_loader.resolve_names import resolve_name
from namel3ss.module_loader.types import ModuleExports


def resolve_statements(
    stmts: List[ast.Statement],
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

    def _resolve_stmts(body: List[ast.Statement]) -> None:
        resolve_statements(
            body,
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
        )

    for stmt in stmts:
        if isinstance(stmt, (ast.Let, ast.Set)):
            _resolve_expr(stmt.expression)
        if isinstance(stmt, ast.AskAIStmt):
            stmt.ai_name = resolve_name(
                stmt.ai_name,
                kind="ai",
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
                line=stmt.line,
                column=stmt.column,
            )
        elif isinstance(stmt, ast.RunAgentStmt):
            stmt.agent_name = resolve_name(
                stmt.agent_name,
                kind="agent",
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
                line=stmt.line,
                column=stmt.column,
            )
        elif isinstance(stmt, ast.RunAgentsParallelStmt):
            for entry in stmt.entries:
                entry.agent_name = resolve_name(
                    entry.agent_name,
                    kind="agent",
                    module_name=module_name,
                    alias_map=alias_map,
                    local_defs=local_defs,
                    exports_map=exports_map,
                    context_label=context_label,
                    line=entry.line,
                    column=entry.column,
                )
        elif isinstance(stmt, ast.Save):
            stmt.record_name = resolve_name(
                stmt.record_name,
                kind="record",
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
                line=stmt.line,
                column=stmt.column,
            )
        elif isinstance(stmt, ast.Create):
            stmt.record_name = resolve_name(
                stmt.record_name,
                kind="record",
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
                line=stmt.line,
                column=stmt.column,
            )
            _resolve_expr(stmt.values)
        elif isinstance(stmt, ast.Find):
            stmt.record_name = resolve_name(
                stmt.record_name,
                kind="record",
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
                line=stmt.line,
                column=stmt.column,
            )
            _resolve_expr(stmt.predicate)
        if isinstance(stmt, ast.If):
            _resolve_expr(stmt.condition)
            _resolve_stmts(stmt.then_body)
            _resolve_stmts(stmt.else_body)
        elif isinstance(stmt, ast.Repeat):
            _resolve_expr(stmt.count)
            _resolve_stmts(stmt.body)
        elif isinstance(stmt, ast.RepeatWhile):
            _resolve_expr(stmt.condition)
            _resolve_stmts(stmt.body)
        elif isinstance(stmt, ast.ForEach):
            _resolve_expr(stmt.iterable)
            _resolve_stmts(stmt.body)
        elif isinstance(stmt, ast.ParallelBlock):
            for task in stmt.tasks:
                _resolve_stmts(task.body)
        elif isinstance(stmt, ast.Match):
            _resolve_expr(stmt.expression)
            for case in stmt.cases:
                _resolve_expr(case.pattern)
                _resolve_stmts(case.body)
            if stmt.otherwise:
                _resolve_stmts(stmt.otherwise)
        elif isinstance(stmt, ast.TryCatch):
            _resolve_stmts(stmt.try_body)
            _resolve_stmts(stmt.catch_body)
        elif isinstance(stmt, ast.Return):
            _resolve_expr(stmt.expression)

def resolve_page_item(
    item: ast.PageItem,
    *,
    module_name: str | None,
    alias_map: Dict[str, str],
    local_defs: Dict[str, set[str]],
    exports_map: Dict[str, ModuleExports],
    context_label: str,
) -> None:
    if isinstance(item, ast.FormItem):
        item.record_name = resolve_name(
            item.record_name,
            kind="record",
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
            line=item.line,
            column=item.column,
        )
        return
    if isinstance(item, ast.TableItem):
        item.record_name = resolve_name(
            item.record_name,
            kind="record",
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
            line=item.line,
            column=item.column,
        )
        if item.row_actions:
            for action in item.row_actions:
                if action.kind == "call_flow" and action.flow_name:
                    action.flow_name = resolve_name(
                        action.flow_name,
                        kind="flow",
                        module_name=module_name,
                        alias_map=alias_map,
                        local_defs=local_defs,
                        exports_map=exports_map,
                        context_label=context_label,
                        line=action.line,
                        column=action.column,
                    )
        return
    if isinstance(item, ast.ListItem):
        item.record_name = resolve_name(
            item.record_name,
            kind="record",
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
            line=item.line,
            column=item.column,
        )
        if item.actions:
            for action in item.actions:
                if action.kind == "call_flow" and action.flow_name:
                    action.flow_name = resolve_name(
                        action.flow_name,
                        kind="flow",
                        module_name=module_name,
                        alias_map=alias_map,
                        local_defs=local_defs,
                        exports_map=exports_map,
                        context_label=context_label,
                        line=action.line,
                        column=action.column,
                    )
        return
    if isinstance(item, ast.ChartItem) and item.record_name:
        item.record_name = resolve_name(
            item.record_name,
            kind="record",
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
            line=item.line,
            column=item.column,
        )
        return
    if isinstance(item, ast.UseUIPackItem):
        item.pack_name = resolve_name(
            item.pack_name,
            kind="ui_pack",
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
            line=item.line,
            column=item.column,
        )
        return
    if isinstance(item, ast.ButtonItem):
        item.flow_name = resolve_name(
            item.flow_name,
            kind="flow",
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
            line=item.line,
            column=item.column,
        )
        return
    if isinstance(item, ast.ChatItem):
        for child in item.children:
            if isinstance(child, ast.ChatComposerItem):
                child.flow_name = resolve_name(
                    child.flow_name,
                    kind="flow",
                    module_name=module_name,
                    alias_map=alias_map,
                    local_defs=local_defs,
                    exports_map=exports_map,
                    context_label=context_label,
                    line=child.line,
                    column=child.column,
                )
        return
    if isinstance(item, ast.CardItem):
        if item.actions:
            for action in item.actions:
                if action.kind == "call_flow" and action.flow_name:
                    action.flow_name = resolve_name(
                        action.flow_name,
                        kind="flow",
                        module_name=module_name,
                        alias_map=alias_map,
                        local_defs=local_defs,
                        exports_map=exports_map,
                        context_label=context_label,
                        line=action.line,
                        column=action.column,
                    )
        for child in item.children:
            resolve_page_item(
                child,
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
            )
        return
    if isinstance(item, ast.TabsItem):
        for tab in item.tabs:
            for child in tab.children:
                resolve_page_item(
                    child,
                    module_name=module_name,
                    alias_map=alias_map,
                    local_defs=local_defs,
                    exports_map=exports_map,
                    context_label=context_label,
                )
        return
    if isinstance(item, (ast.SectionItem, ast.CardGroupItem, ast.RowItem, ast.ColumnItem)):
        for child in item.children:
            resolve_page_item(
                child,
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
            )

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


__all__ = ["resolve_expression", "resolve_page_item", "resolve_statements"]
