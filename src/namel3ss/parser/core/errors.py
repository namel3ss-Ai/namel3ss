from __future__ import annotations

from namel3ss.errors.base import Namel3ssError


def raise_parse_error(token, message: str, *, details: dict | None = None) -> None:
    raise Namel3ssError(message, line=token.line, column=token.column, details=details)


__all__ = ["raise_parse_error"]
