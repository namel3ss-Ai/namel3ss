from __future__ import annotations

from namel3ss.errors.base import Namel3ssError


def read_attr_name(parser, *, context: str) -> str:
    tok = parser._current()
    if not isinstance(tok.value, str) or tok.type == "STRING":
        raise Namel3ssError(f"Expected {context}", line=tok.line, column=tok.column)
    parser._advance()
    return tok.value


__all__ = ["read_attr_name"]
