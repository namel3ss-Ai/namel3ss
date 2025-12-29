from __future__ import annotations

"""Legacy shim for control flow statements."""

from namel3ss.parser.stmt.foreach import parse_for_each
from namel3ss.parser.stmt.if_stmt import parse_if
from namel3ss.parser.stmt.match import parse_match
from namel3ss.parser.stmt.repeat import parse_repeat
from namel3ss.parser.stmt.return_stmt import parse_return
from namel3ss.parser.stmt.trycatch import parse_try

__all__ = [
    "parse_for_each",
    "parse_if",
    "parse_match",
    "parse_repeat",
    "parse_return",
    "parse_try",
]
