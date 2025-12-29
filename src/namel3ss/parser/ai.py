from __future__ import annotations

"""Legacy shim for AI parsing."""

from namel3ss.parser.decl.ai import parse_ai_decl
from namel3ss.parser.stmt.ask_ai import parse_ask_stmt

__all__ = ["parse_ai_decl", "parse_ask_stmt"]
