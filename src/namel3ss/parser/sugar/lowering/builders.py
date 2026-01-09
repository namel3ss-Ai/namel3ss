from __future__ import annotations

from decimal import Decimal

from namel3ss.ast import nodes as ast


def _metric_meta(metric: str) -> tuple[int, str]:
    if metric == "ai_calls":
        return 1, "AI calls"
    if metric == "tool_calls":
        return 2, "Tool calls"
    return 3, "Policy violations"


def _timeline_event(*, seq: int, stage: str, detail: ast.Expression, line: int, column: int) -> list[ast.Statement]:
    statements: list[ast.Statement] = []
    statements.extend(
        _set_state_block(
            ["timeline_event"],
            {
                "run_id": _state_expr(["run_id"], line, column),
                "seq": _number(seq, line, column),
                "stage": ast.Literal(value=stage, line=line, column=column),
                "detail": detail,
            },
            line,
            column,
        )
    )
    statements.append(
        ast.Create(
            record_name="TimelineEvent",
            values=_state_expr(["timeline_event"], line, column),
            target="event",
            line=line,
            column=column,
        )
    )
    return statements


def _delete_by_run_id(record_name: str, line: int, column: int) -> list[ast.Statement]:
    predicate = _eq(_var("run_id", line, column), _state_expr(["run_id"], line, column), line, column)
    return [ast.Delete(record_name=record_name, predicate=predicate, line=line, column=column)]


def _delete_metric(label: str, line: int, column: int) -> list[ast.Statement]:
    predicate = _and_predicate(
        _eq(_var("run_id", line, column), _state_expr(["run_id"], line, column), line, column),
        _eq(_var("label", line, column), ast.Literal(value=label, line=line, column=column), line, column),
        line,
        column,
    )
    return [ast.Delete(record_name="DebugMetric", predicate=predicate, line=line, column=column)]


def _set_state_block(prefix: list[str], fields: dict[str, ast.Expression], line: int, column: int) -> list[ast.Statement]:
    statements: list[ast.Statement] = []
    for name, expr in fields.items():
        statements.append(
            _set_state(prefix + [name], expr, line, column)
        )
    return statements


def _write_metric(label: str, seq: int, metric: str, line: int, column: int) -> list[ast.Statement]:
    statements: list[ast.Statement] = []
    statements.extend(
        _set_state_block(
            ["debug_metric"],
            {
                "run_id": _state_expr(["run_id"], line, column),
                "seq": _number(seq, line, column),
                "label": ast.Literal(value=label, line=line, column=column),
                "value": _state_expr([metric], line, column),
            },
            line,
            column,
        )
    )
    statements.append(
        ast.Create(
            record_name="DebugMetric",
            values=_state_expr(["debug_metric"], line, column),
            target="metric",
            line=line,
            column=column,
        )
    )
    return statements


def _set_state(path: list[str], expr: ast.Expression, line: int, column: int) -> ast.Set:
    return ast.Set(target=ast.StatePath(path=path, line=line, column=column), expression=expr, line=line, column=column)


def _state_expr(path: list[str], line: int, column: int) -> ast.StatePath:
    return ast.StatePath(path=path, line=line, column=column)


def _number(value: int, line: int, column: int) -> ast.Literal:
    return ast.Literal(value=Decimal(value), line=line, column=column)


def _var(name: str, line: int, column: int) -> ast.VarReference:
    return ast.VarReference(name=name, line=line, column=column)


def _eq(left: ast.Expression, right: ast.Expression, line: int, column: int) -> ast.Comparison:
    return ast.Comparison(kind="eq", left=left, right=right, line=line, column=column)


def _and_predicate(left: ast.Expression, right: ast.Expression, line: int, column: int) -> ast.Expression:
    return ast.BinaryOp(op="and", left=left, right=right, line=line, column=column)
