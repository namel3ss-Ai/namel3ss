from __future__ import annotations

from typing import Callable

from namel3ss.ast import nodes as ast
from namel3ss.parser.generated.grammar_snapshot import GRAMMAR_PATH, GRAMMAR_SHA256, RULE_NAMES


def parse_with_generated_parser(
    source: str,
    *,
    parse_impl: Callable[..., ast.Program],
    allow_legacy_type_aliases: bool = True,
    allow_capsule: bool = False,
    require_spec: bool = True,
    lower_sugar: bool = True,
) -> ast.Program:
    # Grammar snapshot metadata is loaded so parser inputs stay tied to the
    # committed grammar contract.
    _ = (GRAMMAR_PATH, GRAMMAR_SHA256, RULE_NAMES)
    return parse_impl(
        source,
        allow_legacy_type_aliases=allow_legacy_type_aliases,
        allow_capsule=allow_capsule,
        require_spec=require_spec,
        lower_sugar=lower_sugar,
    )


__all__ = ["parse_with_generated_parser"]
