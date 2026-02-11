from __future__ import annotations

from collections.abc import Mapping

from namel3ss.ir.validation.includes_validation import DIAGNOSTICS_TRACE_WARNING_MESSAGE
from namel3ss.validation import add_warning


def append_composition_include_warnings(program, warnings: list | None) -> None:
    if warnings is None:
        return
    entries = getattr(program, "composition_include_warnings", None)
    if not isinstance(entries, list):
        return
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        message = str(entry.get("message") or "").strip()
        if not message:
            continue
        add_warning(
            warnings,
            code=str(entry.get("code") or "composition.include.warning"),
            message=message,
            line=_coerce_line(entry.get("line")),
            column=_coerce_line(entry.get("column")),
            category="composition",
        )


def append_diagnostics_trace_warning(program, warnings: list | None) -> None:
    if warnings is None:
        return
    capabilities = set(getattr(program, "capabilities", ()) or ())
    if "diagnostics.trace" in capabilities:
        return
    usage = getattr(program, "retrieval_flow_usage", None)
    controls = usage.get("controls") if isinstance(usage, dict) else None
    if not isinstance(controls, dict):
        return
    has_retrieval_controls = any(
        isinstance(control, dict) and control.get("available") is True
        for control in controls.values()
    )
    if not has_retrieval_controls:
        return
    add_warning(
        warnings,
        code="diagnostics.trace.disabled",
        message=DIAGNOSTICS_TRACE_WARNING_MESSAGE,
        category="diagnostics",
    )


def _coerce_line(value: object) -> int | None:
    if isinstance(value, int) and value > 0:
        return value
    return None


__all__ = ["append_composition_include_warnings", "append_diagnostics_trace_warning"]
