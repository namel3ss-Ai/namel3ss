from __future__ import annotations

from typing import Callable

from namel3ss.ast import nodes as ast
from namel3ss.parser.generated.grammar_snapshot import GRAMMAR_PATH, GRAMMAR_SHA256, RULE_NAMES


def parse_with_generated_parser(
    source: str,
    *,
    legacy_parse: Callable[..., ast.Program],
    allow_legacy_type_aliases: bool = True,
    allow_capsule: bool = False,
    require_spec: bool = True,
    lower_sugar: bool = True,
) -> ast.Program:
    # Transitional backend: grammar snapshot is authoritative, and parsing
    # still delegates to the legacy parser implementation while migration lands.
    _ = (GRAMMAR_PATH, GRAMMAR_SHA256, RULE_NAMES)
    return legacy_parse(
        source,
        allow_legacy_type_aliases=allow_legacy_type_aliases,
        allow_capsule=allow_capsule,
        require_spec=require_spec,
        lower_sugar=lower_sugar,
    )


__all__ = ["parse_with_generated_parser"]
