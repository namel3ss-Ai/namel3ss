from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError


def _ensure_no_top_level_visibility(items: list[ast.PageItem], source: ast.PageItem) -> None:
    for entry in items:
        if getattr(entry, "visibility", None) is not None or getattr(entry, "visibility_rule", None) is not None:
            raise Namel3ssError(
                "Pattern visibility cannot be combined with item visibility",
                line=source.line,
                column=source.column,
            )


def _apply_visibility(item: ast.PageItem, visibility: ast.Expression) -> ast.PageItem:
    item.visibility = visibility
    return item


def _apply_visibility_rule(
    item: ast.PageItem,
    visibility_rule: ast.VisibilityRule | ast.VisibilityExpressionRule,
) -> ast.PageItem:
    item.visibility_rule = visibility_rule
    return item


__all__ = ["_apply_visibility", "_apply_visibility_rule", "_ensure_no_top_level_visibility"]
