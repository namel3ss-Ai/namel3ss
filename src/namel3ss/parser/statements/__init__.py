from __future__ import annotations

"""Legacy shim for statement parsing facade."""

from namel3ss.parser.stmt.common import parse_statement, parse_target, validate_match_pattern
from namel3ss.parser.stmt.create import parse_create
from namel3ss.parser.stmt.find import parse_find
from namel3ss.parser.stmt.foreach import parse_for_each
from namel3ss.parser.stmt.if_stmt import parse_if
from namel3ss.parser.stmt.let import parse_let
from namel3ss.parser.stmt.match import parse_match
from namel3ss.parser.stmt.repeat import parse_repeat
from namel3ss.parser.stmt.return_stmt import parse_return
from namel3ss.parser.stmt.save import parse_save
from namel3ss.parser.stmt.set import parse_set
from namel3ss.parser.stmt.theme import parse_set_theme
from namel3ss.parser.stmt.trycatch import parse_try

__all__ = [
    "parse_statement",
    "parse_let",
    "parse_set",
    "parse_set_theme",
    "parse_if",
    "parse_return",
    "parse_repeat",
    "parse_for_each",
    "parse_match",
    "parse_try",
    "parse_save",
    "parse_create",
    "parse_find",
    "parse_target",
    "validate_match_pattern",
]
