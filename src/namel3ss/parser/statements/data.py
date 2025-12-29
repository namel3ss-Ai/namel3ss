from __future__ import annotations

"""Legacy shim for data statements."""

from namel3ss.parser.stmt.create import parse_create
from namel3ss.parser.stmt.find import parse_find
from namel3ss.parser.stmt.save import parse_save

__all__ = ["parse_create", "parse_find", "parse_save"]
