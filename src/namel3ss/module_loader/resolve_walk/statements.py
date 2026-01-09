from __future__ import annotations

from typing import Dict, List

from namel3ss.ast import nodes as ast
from namel3ss.module_loader.resolve_names import resolve_name
from namel3ss.module_loader.types import ModuleExports
from namel3ss.module_loader.resolve_walk.expressions import resolve_expression


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
        elif isinstance(stmt, ast.Update):
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
            for update in stmt.updates:
                _resolve_expr(update.expression)
        elif isinstance(stmt, ast.Delete):
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


__all__ = ["resolve_statements"]
