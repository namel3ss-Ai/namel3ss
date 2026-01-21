from __future__ import annotations

import re
from decimal import Decimal

from namel3ss.ast import nodes as ast
from namel3ss.parser.sugar import grammar as sugar
from namel3ss.parser.sugar.lowering.expressions import _lower_expression


_CAMEL_BOUNDARY = re.compile(r"([a-z0-9])([A-Z])")


def _lower_latest_let(stmt: ast.Let, expr: sugar.LatestRecordExpr) -> list[ast.Statement]:
    line = stmt.line
    column = stmt.column
    slug = _record_results_slug(expr.record_name)
    results_name = f"{slug}_results"
    count_name = f"__latest_{slug}_count"
    index_name = f"__latest_{slug}_index"
    find_stmt = ast.Find(
        record_name=expr.record_name,
        predicate=ast.Literal(value=True, line=line, column=column),
        line=line,
        column=column,
    )
    count_stmt = ast.Let(
        name=count_name,
        expression=ast.ListOpExpr(
            kind="length",
            target=ast.VarReference(name=results_name, line=line, column=column),
            line=line,
            column=column,
        ),
        constant=False,
        line=line,
        column=column,
    )
    condition = ast.Comparison(
        kind="gt",
        left=ast.VarReference(name=count_name, line=line, column=column),
        right=ast.Literal(value=Decimal(0), line=line, column=column),
        line=line,
        column=column,
    )
    then_body = [
        ast.Let(
            name=index_name,
            expression=ast.BinaryOp(
                op="-",
                left=ast.VarReference(name=count_name, line=line, column=column),
                right=ast.Literal(value=Decimal(1), line=line, column=column),
                line=line,
                column=column,
            ),
            constant=False,
            line=line,
            column=column,
        ),
        ast.Let(
            name=stmt.name,
            expression=ast.ListOpExpr(
                kind="get",
                target=ast.VarReference(name=results_name, line=line, column=column),
                index=ast.VarReference(name=index_name, line=line, column=column),
                line=line,
                column=column,
            ),
            constant=stmt.constant,
            line=line,
            column=column,
        ),
    ]
    else_body = [
        ast.Let(
            name=stmt.name,
            expression=ast.Literal(value=None, line=line, column=column),
            constant=stmt.constant,
            line=line,
            column=column,
        )
    ]
    return [
        find_stmt,
        count_stmt,
        ast.If(
            condition=condition,
            then_body=then_body,
            else_body=else_body,
            line=line,
            column=column,
        ),
    ]


def _lower_require_latest(stmt: sugar.RequireLatestStmt) -> list[ast.Statement]:
    line = stmt.line
    column = stmt.column
    results_slug = _record_results_slug(stmt.record_name)
    results_name = f"{results_slug}_results"
    count_name = f"__latest_{results_slug}_count"
    index_name = f"__latest_{results_slug}_index"
    missing_value = f"missing_{_record_missing_slug(stmt.record_name)}"
    find_stmt = ast.Find(
        record_name=stmt.record_name,
        predicate=ast.Literal(value=True, line=line, column=column),
        line=line,
        column=column,
    )
    count_stmt = ast.Let(
        name=count_name,
        expression=ast.ListOpExpr(
            kind="length",
            target=ast.VarReference(name=results_name, line=line, column=column),
            line=line,
            column=column,
        ),
        constant=False,
        line=line,
        column=column,
    )
    # The message stays user-controlled text; missing records return a stable sentinel.
    missing_guard = ast.If(
        condition=ast.Comparison(
            kind="eq",
            left=ast.VarReference(name=count_name, line=line, column=column),
            right=ast.Literal(value=Decimal(0), line=line, column=column),
            line=line,
            column=column,
        ),
        then_body=[
            ast.Set(
                target=ast.StatePath(path=["status", "message"], line=line, column=column),
                expression=ast.Literal(value=stmt.message, line=line, column=column),
                line=line,
                column=column,
            ),
            ast.Return(
                expression=ast.Literal(value=missing_value, line=line, column=column),
                line=line,
                column=column,
            )
        ],
        else_body=[],
        line=line,
        column=column,
    )
    index_stmt = ast.Let(
        name=index_name,
        expression=ast.BinaryOp(
            op="-",
            left=ast.VarReference(name=count_name, line=line, column=column),
            right=ast.Literal(value=Decimal(1), line=line, column=column),
            line=line,
            column=column,
        ),
        constant=False,
        line=line,
        column=column,
    )
    target_stmt = ast.Let(
        name=stmt.target,
        expression=ast.ListOpExpr(
            kind="get",
            target=ast.VarReference(name=results_name, line=line, column=column),
            index=ast.VarReference(name=index_name, line=line, column=column),
            line=line,
            column=column,
        ),
        constant=False,
        line=line,
        column=column,
    )
    return [find_stmt, count_stmt, missing_guard, index_stmt, target_stmt]


def _lower_clear(stmt: sugar.ClearStmt) -> list[ast.Statement]:
    line = stmt.line
    column = stmt.column
    return [
        ast.Delete(
            record_name=record_name,
            predicate=ast.Literal(value=True, line=line, column=column),
            line=line,
            column=column,
        )
        for record_name in stmt.record_names
    ]


def _lower_save_record(stmt: sugar.SaveRecordStmt) -> list[ast.Statement]:
    line = stmt.line
    column = stmt.column
    record_slug = _record_missing_slug(stmt.record_name)
    temp_name = f"__save_{record_slug}_payload"
    binding_name = record_slug
    statements: list[ast.Statement] = []
    for field in stmt.fields:
        statements.append(
            ast.Set(
                target=ast.StatePath(path=[temp_name] + field.path, line=field.line, column=field.column),
                expression=_lower_expression(field.expression),
                line=field.line,
                column=field.column,
            )
        )
    statements.append(
        ast.Create(
            record_name=stmt.record_name,
            values=ast.StatePath(path=[temp_name], line=line, column=column),
            target=binding_name,
            line=line,
            column=column,
        )
    )
    return statements


def _lower_notice(stmt: sugar.NoticeStmt) -> list[ast.Statement]:
    line = stmt.line
    column = stmt.column
    return [
        ast.Set(
            target=ast.StatePath(path=["notice"], line=line, column=column),
            expression=ast.Literal(value=stmt.message, line=line, column=column),
            line=line,
            column=column,
        )
    ]


def _record_results_slug(record_name: str) -> str:
    parts = [part.lower() for part in record_name.split(".") if part]
    return "_".join(parts) if parts else "record"


def _record_missing_slug(record_name: str) -> str:
    parts = [part for part in record_name.split(".") if part]
    if not parts:
        return "record"
    normalized = [_CAMEL_BOUNDARY.sub(r"\1_\2", part).lower() for part in parts]
    return "_".join(normalized)


__all__ = [
    "_CAMEL_BOUNDARY",
    "_lower_clear",
    "_lower_latest_let",
    "_lower_notice",
    "_lower_require_latest",
    "_lower_save_record",
    "_record_missing_slug",
    "_record_results_slug",
]
