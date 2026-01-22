from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.parser.core.helpers import parse_reference_name


METRIC_KINDS = {"counter", "timing"}
COUNTER_OPS = {"increment", "add", "set"}
TIMING_OPS = {"record"}


def parse_metric(parser) -> ast.MetricStmt:
    metric_tok = parser._advance()
    kind_tok = parser._current()
    if kind_tok.type != "IDENT":
        raise Namel3ssError(
            build_guidance_message(
                what="Metric statement is missing a kind.",
                why="Metrics must declare counter or timing.",
                fix="Add counter or timing after metric.",
                example='metric counter "requests" increment',
            ),
            line=kind_tok.line,
            column=kind_tok.column,
        )
    kind = str(kind_tok.value).lower()
    if kind not in METRIC_KINDS:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unknown metric kind '{kind_tok.value}'.",
                why="Metrics must be counters or timings.",
                fix="Use counter or timing.",
                example='metric timing "render" record 4',
            ),
            line=kind_tok.line,
            column=kind_tok.column,
        )
    parser._advance()
    name = parse_reference_name(parser, context="metric")
    op_tok = parser._current()
    if op_tok.type not in {"IDENT", "RECORD", "SET"}:
        raise Namel3ssError(
            build_guidance_message(
                what="Metric statement is missing an operation.",
                why="Counters use increment/add/set; timings use record.",
                fix="Add a metric operation after the name.",
                example='metric counter "requests" add 3',
            ),
            line=op_tok.line,
            column=op_tok.column,
        )
    operation = str(op_tok.value).lower()
    valid_ops = COUNTER_OPS if kind == "counter" else TIMING_OPS
    if operation not in valid_ops:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unsupported metric operation '{op_tok.value}'.",
                why=f"{kind.capitalize()} metrics only support {', '.join(sorted(valid_ops))}.",
                fix="Use a supported metric operation.",
                example='metric counter "requests" increment',
            ),
            line=op_tok.line,
            column=op_tok.column,
        )
    parser._advance()
    value_expr = None
    if parser._current().type not in {"NEWLINE", "DEDENT", "EOF", "WITH"}:
        value_expr = parser._parse_expression()
    if value_expr is None and operation in {"add", "set", "record"}:
        tok = parser._current()
        raise Namel3ssError(
            build_guidance_message(
                what=f"Metric operation '{operation}' is missing a value.",
                why="This metric operation requires a numeric value.",
                fix="Provide a value after the operation.",
                example='metric counter "requests" add 2',
            ),
            line=tok.line,
            column=tok.column,
        )
    labels_expr = None
    if parser._match("WITH"):
        if parser._current().type in {"NEWLINE", "DEDENT", "EOF"}:
            tok = parser._current()
            raise Namel3ssError(
                build_guidance_message(
                    what="Metric labels are missing.",
                    why="The with clause must include a labels object.",
                    fix="Provide a map expression after with.",
                    example='metric counter "requests" increment with map:\n  "route" is "/api/orders"',
                ),
                line=tok.line,
                column=tok.column,
            )
        labels_expr = parser._parse_expression()
    return ast.MetricStmt(
        kind=kind,
        name=name,
        operation=operation,
        value=value_expr,
        labels=labels_expr,
        line=metric_tok.line,
        column=metric_tok.column,
    )


__all__ = ["parse_metric"]
