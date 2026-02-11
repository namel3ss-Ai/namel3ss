from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.program_loader import IncludeWarning

MISSING_INCLUDES_CAPABILITY_MESSAGE = (
    "Capability missing: composition.includes is required to use 'include' directives. "
    "Add 'capability is composition.includes' to the manifest."
)

DIAGNOSTICS_TRACE_WARNING_MESSAGE = (
    "Warning: Retrieval trace diagnostics are disabled (missing capability diagnostics.trace)."
)


def ensure_include_capability(program: ast.Program) -> None:
    includes = list(getattr(program, "includes", []) or [])
    if not includes:
        return
    capabilities = set(getattr(program, "capabilities", []) or [])
    if "composition.includes" in capabilities:
        return
    first = includes[0]
    raise Namel3ssError(
        MISSING_INCLUDES_CAPABILITY_MESSAGE,
        line=getattr(first, "line", None),
        column=getattr(first, "column", None),
    )


def normalize_include_warnings(warnings: Iterable[IncludeWarning] | None) -> list[dict[str, object]]:
    if warnings is None:
        return []
    normalized = [asdict(item) for item in warnings if isinstance(item, IncludeWarning)]
    normalized.sort(
        key=lambda item: (
            str(item.get("file") or ""),
            int(item.get("line") or 0),
            int(item.get("column") or 0),
            str(item.get("code") or ""),
            str(item.get("message") or ""),
        )
    )
    return normalized


__all__ = [
    "DIAGNOSTICS_TRACE_WARNING_MESSAGE",
    "MISSING_INCLUDES_CAPABILITY_MESSAGE",
    "ensure_include_capability",
    "normalize_include_warnings",
]
