from __future__ import annotations

from namel3ss.contract.model import ContractPack


_MAX_NAMES = 5


def render_exists(pack: ContractPack) -> str:
    lines: list[str] = []
    lines.append("namel3ss exists")
    lines.append("")
    lines.append("Spec")
    lines.append(f"- version: {pack.spec_version}")
    lines.append(f"- source hash: {pack.source_hash}")

    lines.append("")
    lines.append("Program summary")
    summary = pack.program_summary
    if isinstance(summary, dict):
        lines.append(_summary_line("flows", summary.get("flows")))
        lines.append(_summary_line("records", summary.get("records")))
        lines.append(_summary_line("pages", summary.get("pages")))
        lines.append(_summary_line("ai", summary.get("ais")))
        lines.append(_summary_line("tools", summary.get("tools")))
        lines.append(_summary_line("agents", summary.get("agents")))
        lines.append(_identity_line(summary.get("identity")))
    else:
        lines.append("- none recorded")

    lines.append("")
    lines.append("Features used")
    lines.extend(_list_lines(pack.features_used))

    lines.append("")
    lines.append("Capabilities required")
    lines.extend(_list_lines(pack.capabilities_required))

    lines.append("")
    lines.append("Warnings")
    lines.extend(_list_lines(pack.warnings))

    return "\n".join(lines)


def _summary_line(label: str, entry: object) -> str:
    if not isinstance(entry, dict):
        return f"- {label}: none recorded"
    names = entry.get("names") or []
    if not isinstance(names, list) or not names:
        return f"- {label}: none recorded"
    return f"- {label}: {len(names)} ({_format_names(names)})"


def _identity_line(entry: object) -> str:
    if not isinstance(entry, dict) or not entry.get("present"):
        return "- identity: none recorded"
    name = entry.get("name") or ""
    return f"- identity: {name}" if name else "- identity: recorded"


def _list_lines(values: list[str]) -> list[str]:
    if not values:
        return ["- none recorded"]
    return [f"- {value}" for value in values]


def _format_names(names: list[str]) -> str:
    if len(names) <= _MAX_NAMES:
        return ", ".join(names)
    return ", ".join(names[:_MAX_NAMES]) + ", ..."


__all__ = ["render_exists"]
