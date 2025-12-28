from __future__ import annotations

from namel3ss.runtime.memory_handoff.select import HandoffSelection


def briefing_lines(selection: HandoffSelection) -> list[str]:
    lines = ["Here is what you need to know."]
    lines.append(_count_line("Decision items count is", selection.decision_count))
    lines.append(_count_line("Pending proposals count is", selection.proposal_count))
    lines.append(_count_line("Conflicts count is", selection.conflict_count))
    lines.append(_count_line("Active rules count is", selection.rules_count))
    lines.append(_count_line("Impact warnings count is", selection.impact_count))
    return lines


def _count_line(prefix: str, count: int) -> str:
    return f"{prefix} {int(count)}."


__all__ = ["briefing_lines"]
