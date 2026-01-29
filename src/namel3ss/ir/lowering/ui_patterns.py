from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.lowering.ui_packs import expand_page_items
from namel3ss.ir.lowering.ui_patterns_expand import expand_pattern_items
from namel3ss.ui.patterns import builtin_patterns
from namel3ss.ui.patterns.model import PatternDefinition


def build_pattern_index(
    patterns: list[ast.UIPatternDecl],
    pack_index: dict[str, ast.UIPackDecl],
) -> dict[str, PatternDefinition]:
    index: dict[str, PatternDefinition] = {}
    for builtin in builtin_patterns():
        if builtin.name in index:
            raise Namel3ssError(f"pattern '{builtin.name}' is declared more than once")
        index[builtin.name] = builtin
    for pattern in patterns:
        if pattern.name in index:
            raise Namel3ssError(
                f"pattern '{pattern.name}' is declared more than once",
                line=pattern.line,
                column=pattern.column,
            )
        expanded_items = expand_page_items(
            pattern.items,
            pack_index,
            allow_tabs=True,
            allow_overlays=True,
            columns_only=False,
            page_name=pattern.name,
        )
        index[pattern.name] = PatternDefinition(
            name=pattern.name,
            parameters=list(pattern.parameters),
            items=expanded_items,
            builder=None,
        )
    return index


__all__ = ["build_pattern_index", "expand_pattern_items"]
