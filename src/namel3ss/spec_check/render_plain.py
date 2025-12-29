from __future__ import annotations

from namel3ss.spec_check.model import SpecPack


def render_when(pack: SpecPack) -> str:
    decision = pack.decision
    lines: list[str] = []
    lines.append("spec check")

    lines.append("")
    lines.append("Declared")
    lines.extend(_bullet_lines([f"spec: {decision.declared_spec}"]))

    lines.append("")
    lines.append("Engine supports")
    lines.extend(_bullet_lines(list(decision.engine_supported)))

    lines.append("")
    lines.append("Required capabilities")
    lines.extend(_bullet_lines(list(decision.required_capabilities)))

    lines.append("")
    lines.append("Unsupported capabilities")
    lines.extend(_bullet_lines(list(decision.unsupported_capabilities)))

    lines.append("")
    lines.append("Result")
    lines.extend(_bullet_lines([f"status: {decision.status}", decision.what]))

    if decision.status == "blocked":
        lines.append("")
        lines.append("How to fix")
        lines.extend(_bullet_lines(list(decision.fix)))

    return "\n".join(lines)


def _bullet_lines(items: list[str]) -> list[str]:
    cleaned = [item for item in items if item]
    if not cleaned:
        return ["- none recorded"]
    return [f"- {item}" for item in cleaned]


__all__ = ["render_when"]
