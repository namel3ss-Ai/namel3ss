from __future__ import annotations

"""Legacy shim for let and set statements."""

from namel3ss.parser.stmt.let import parse_let
from namel3ss.parser.stmt.set import parse_set
from namel3ss.parser.stmt.theme import parse_set_theme

__all__ = ["parse_let", "parse_set", "parse_set_theme"]
