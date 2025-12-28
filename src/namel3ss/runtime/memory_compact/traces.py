from __future__ import annotations

from namel3ss.traces.builders import build_memory_compaction


def build_compaction_event(
    *,
    ai_profile: str,
    session: str,
    space: str,
    lane: str,
    phase_id: str,
    owner: str,
    action: str,
    reason: str,
    items_removed_count: int,
    summary_written: bool,
    summary_lines: list[str] | None = None,
) -> dict:
    lines: list[str] = []
    lines.append(f"Action is {action}.")
    if reason:
        lines.append(f"Reason is {reason}.")
    lines.append(f"Items removed are {int(items_removed_count)}.")
    lines.append("Summary was written." if summary_written else "Summary was not written.")
    if summary_lines:
        lines.extend(summary_lines)
    title = "Memory compaction"
    return build_memory_compaction(
        ai_profile=ai_profile,
        session=session,
        space=space,
        lane=lane,
        phase_id=phase_id,
        owner=owner,
        action=action,
        items_removed_count=int(items_removed_count),
        summary_written=bool(summary_written),
        reason=reason,
        title=title,
        lines=lines,
    )


__all__ = ["build_compaction_event"]
