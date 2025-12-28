from __future__ import annotations

from dataclasses import dataclass

from namel3ss.runtime.memory.events import (
    EVENT_CONTEXT,
    EVENT_CORRECTION,
    EVENT_DECISION,
    EVENT_EXECUTION,
    EVENT_FACT,
    EVENT_PREFERENCE,
    EVENT_RULE,
)
from namel3ss.runtime.memory_timeline.diff import PhaseDiff


@dataclass(frozen=True)
class TeamSummary:
    title: str
    lines: list[str]


def build_team_summary(diff: PhaseDiff) -> TeamSummary:
    lines: list[str] = ["Team memory changed."]
    lines.extend(_count_lines(diff))
    lines.extend(_detail_lines(diff))
    return TeamSummary(title="Team memory summary", lines=lines)


def _count_lines(diff: PhaseDiff) -> list[str]:
    return [
        _count_line("Added items count is", len(diff.added)),
        _count_line("Removed items count is", len(diff.deleted)),
        _count_line("Replaced items count is", len(diff.replaced)),
    ]


def _detail_lines(diff: PhaseDiff) -> list[str]:
    lines: list[str] = []
    added = _counts_by_event_type([item.dedupe_key for item in diff.added])
    deleted = _counts_by_event_type([item.dedupe_key for item in diff.deleted])
    replaced = _counts_by_event_type([after.dedupe_key for _, after, _ in diff.replaced])
    for event_type in sorted(added):
        lines.append(_count_line(f"Added {_label_for_event(event_type)} count is", added[event_type]))
    for event_type in sorted(deleted):
        lines.append(_count_line(f"Removed {_label_for_event(event_type)} count is", deleted[event_type]))
    for event_type in sorted(replaced):
        lines.append(_count_line(f"Updated {_label_for_event(event_type)} count is", replaced[event_type]))
    return lines


def _counts_by_event_type(keys: list[str | None]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for key in keys:
        event_type = _event_type_from_key(key)
        counts[event_type] = counts.get(event_type, 0) + 1
    return counts


def _event_type_from_key(key: str | None) -> str:
    if not key:
        return "item"
    text = str(key)
    if ":" in text:
        return text.split(":", 1)[0]
    return text


def _label_for_event(event_type: str) -> str:
    labels = {
        EVENT_DECISION: "decision",
        EVENT_RULE: "rule",
        EVENT_EXECUTION: "tool outcome",
        EVENT_FACT: "fact",
        EVENT_PREFERENCE: "preference",
        EVENT_CORRECTION: "correction",
        EVENT_CONTEXT: "context",
    }
    return labels.get(event_type, event_type)


def _count_line(prefix: str, count: int) -> str:
    return f"{prefix} {int(count)}."


__all__ = ["TeamSummary", "build_team_summary"]
