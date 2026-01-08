from __future__ import annotations

from namel3ss.runtime.memory.contract import MemoryItem, MemoryKind
from namel3ss.runtime.memory_handoff.select import HandoffSelection
from namel3ss.runtime.memory_lanes.model import LANE_AGENT, LANE_MY, LANE_SYSTEM, LANE_TEAM


def briefing_lines(selection: HandoffSelection) -> list[str]:
    lines = ["Here is what you need to know."]
    lines.append(_count_line("Decision items count is", selection.decision_count))
    lines.append(_count_line("Pending proposals count is", selection.proposal_count))
    lines.append(_count_line("Conflicts count is", selection.conflict_count))
    lines.append(_count_line("Active rules count is", selection.rules_count))
    lines.append(_count_line("Impact warnings count is", selection.impact_count))
    return lines


def diff_lines(applied_items: list[MemoryItem]) -> list[str]:
    if not applied_items:
        return ["No memory items applied."]
    total = len(applied_items)
    kind_counts = {
        MemoryKind.SHORT_TERM.value: 0,
        MemoryKind.SEMANTIC.value: 0,
        MemoryKind.PROFILE.value: 0,
    }
    lane_counts = {LANE_MY: 0, LANE_AGENT: 0, LANE_TEAM: 0, LANE_SYSTEM: 0}
    for item in applied_items:
        kind_counts[item.kind.value] = kind_counts.get(item.kind.value, 0) + 1
        lane = (item.meta or {}).get("lane")
        if lane in lane_counts:
            lane_counts[lane] += 1
    lines = [f"Applied {total} memory items."]
    kind_parts = [f"{kind} {count}" for kind, count in kind_counts.items() if count]
    if kind_parts:
        lines.append(f"Kinds: {', '.join(kind_parts)}.")
    lane_parts = [f"{lane} {count}" for lane, count in lane_counts.items() if count]
    if lane_parts:
        lines.append(f"Lanes: {', '.join(lane_parts)}.")
    return lines


def _count_line(prefix: str, count: int) -> str:
    return f"{prefix} {int(count)}."


__all__ = ["briefing_lines", "diff_lines"]
