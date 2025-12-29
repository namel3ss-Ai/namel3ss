from __future__ import annotations

from .normalize import stable_bullets, stable_truncate


def render_fix(pack: dict) -> str:
    if pack.get("ok", True):
        return "No errors in the last run."

    error = pack.get("error") or {}
    where = error.get("where") or {}
    impact = error.get("impact") or []
    options = error.get("recovery_options") or []

    lines: list[str] = []
    lines.append("What went wrong")
    lines.append("")
    lines.append("Error")
    if error.get("what"):
        lines.extend(stable_bullets([stable_truncate(str(error.get("what")))]))
    lines.extend(stable_bullets([f"kind: {error.get('kind')}"]))
    if where.get("flow_name"):
        lines.extend(stable_bullets([f"where: flow \"{where.get('flow_name')}\""]))
    if where.get("step_id"):
        lines.extend(stable_bullets([f"step: {where.get('step_id')}"]))
    if where.get("tool_name"):
        lines.extend(stable_bullets([f"tool: {where.get('tool_name')}"]))
    if error.get("why"):
        lines.extend(stable_bullets([f"why: {stable_truncate(str(error.get('why')))}"]))

    lines.append("")
    lines.append("Impact")
    if impact:
        lines.extend(stable_bullets([stable_truncate(str(entry)) for entry in impact]))
    else:
        lines.extend(stable_bullets(["No explicit impact was recorded."]))

    lines.append("")
    lines.append("Recovery options")
    if options:
        option_lines = []
        for option in options:
            title = option.get("title") or "recovery"
            how = option.get("how") or ""
            option_lines.append(f"{title}: {stable_truncate(str(how))}")
        lines.extend(stable_bullets(option_lines))
    else:
        lines.extend(stable_bullets(["No recovery paths were recorded for this error."]))

    return "\n".join(lines).rstrip()


__all__ = ["render_fix"]
