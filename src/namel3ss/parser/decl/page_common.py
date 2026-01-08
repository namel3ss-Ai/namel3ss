from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError


def _match_ident_value(parser, value: str) -> bool:
    tok = parser._current()
    if tok.type == "IDENT" and tok.value == value:
        parser._advance()
        return True
    return False


def _reject_list_transforms(expr: ast.Expression | None) -> None:
    if expr is None:
        return
    if isinstance(expr, (ast.ListMapExpr, ast.ListFilterExpr, ast.ListReduceExpr)):
        raise Namel3ssError(
            "Pages are declarative; list transforms are not allowed in page expressions",
            line=expr.line,
            column=expr.column,
        )
    if isinstance(expr, ast.CallFunctionExpr):
        for arg in expr.arguments:
            _reject_list_transforms(arg.value)
        return
    if isinstance(expr, ast.UnaryOp):
        _reject_list_transforms(expr.operand)
        return
    if isinstance(expr, ast.BinaryOp):
        _reject_list_transforms(expr.left)
        _reject_list_transforms(expr.right)
        return
    if isinstance(expr, ast.Comparison):
        _reject_list_transforms(expr.left)
        _reject_list_transforms(expr.right)
        return
    if isinstance(expr, ast.ListExpr):
        for item in expr.items:
            _reject_list_transforms(item)
        return
    if isinstance(expr, ast.MapExpr):
        for entry in expr.entries:
            _reject_list_transforms(entry.key)
            _reject_list_transforms(entry.value)
        return
    if isinstance(expr, ast.ListOpExpr):
        _reject_list_transforms(expr.target)
        if expr.value is not None:
            _reject_list_transforms(expr.value)
        if expr.index is not None:
            _reject_list_transforms(expr.index)
        return
    if isinstance(expr, ast.MapOpExpr):
        _reject_list_transforms(expr.target)
        if expr.key is not None:
            _reject_list_transforms(expr.key)
        if expr.value is not None:
            _reject_list_transforms(expr.value)
        return


__all__ = ["_match_ident_value", "_reject_list_transforms"]
