from __future__ import annotations

"""Legacy shim for expression parsing."""

from namel3ss.parser.expr.calls import (
    looks_like_tool_call,
    parse_ask_expression,
    parse_old_tool_call,
    parse_tool_call_expr,
)
from namel3ss.parser.expr.comparisons import parse_comparison
from namel3ss.parser.expr.ops import (
    parse_additive,
    parse_and,
    parse_expression,
    parse_multiplicative,
    parse_not,
    parse_or,
    parse_primary,
    parse_unary,
)
from namel3ss.parser.expr.statepath import parse_state_path

__all__ = [
    "looks_like_tool_call",
    "parse_additive",
    "parse_and",
    "parse_ask_expression",
    "parse_comparison",
    "parse_expression",
    "parse_multiplicative",
    "parse_not",
    "parse_old_tool_call",
    "parse_or",
    "parse_primary",
    "parse_state_path",
    "parse_tool_call_expr",
    "parse_unary",
]
