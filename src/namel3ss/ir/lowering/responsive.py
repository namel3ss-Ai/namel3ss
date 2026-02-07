from __future__ import annotations

from namel3ss.ast.responsive import ResponsiveDecl
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.model.responsive import BreakpointSpec, ResponsiveLayout


def lower_responsive_definition(
    definition: ResponsiveDecl | None,
    *,
    capabilities: tuple[str, ...],
) -> ResponsiveLayout | None:
    if definition is None:
        return None
    if "responsive_design" not in set(capabilities):
        # Legacy fallback: ignore responsive metadata when the capability is off.
        return None

    entries = list(getattr(definition, "breakpoints", []) or [])
    if not entries:
        raise Namel3ssError(
            "Responsive block requires at least one breakpoint.",
            line=getattr(definition, "line", None),
            column=getattr(definition, "column", None),
        )

    names: list[str] = []
    values: list[int] = []
    last: int | None = None
    for entry in entries:
        name = str(getattr(entry, "name", "") or "")
        width = int(getattr(entry, "width", 0))
        if not name:
            raise Namel3ssError(
                "Breakpoint name cannot be empty.",
                line=getattr(entry, "line", None),
                column=getattr(entry, "column", None),
            )
        if width < 0:
            raise Namel3ssError(
                f"Breakpoint '{name}' width cannot be negative.",
                line=getattr(entry, "line", None),
                column=getattr(entry, "column", None),
            )
        if last is not None and width <= last:
            raise Namel3ssError(
                "Breakpoints must be ordered from smallest to largest width.",
                line=getattr(entry, "line", None),
                column=getattr(entry, "column", None),
            )
        names.append(name)
        values.append(width)
        last = width

    return ResponsiveLayout(
        breakpoints=BreakpointSpec(
            names=tuple(names),
            values=tuple(values),
            line=getattr(definition, "line", None),
            column=getattr(definition, "column", None),
        ),
        total_columns=12,
        line=getattr(definition, "line", None),
        column=getattr(definition, "column", None),
    )


__all__ = ["lower_responsive_definition"]
