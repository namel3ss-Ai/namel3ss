from __future__ import annotations

"""Legacy shim for capsule and use parsing."""

from namel3ss.parser.decl.capsule import ALLOWED_EXPORT_KINDS, parse_capsule_decl
from namel3ss.parser.decl.use import parse_use_decl

__all__ = ["ALLOWED_EXPORT_KINDS", "parse_capsule_decl", "parse_use_decl"]
