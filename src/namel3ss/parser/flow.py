from __future__ import annotations

"""Legacy shim for flow parsing."""

from namel3ss.parser.decl.flow import parse_flow
from namel3ss.parser.stmt.common import parse_block, parse_statements

__all__ = ["parse_block", "parse_flow", "parse_statements"]
