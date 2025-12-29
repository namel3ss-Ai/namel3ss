from __future__ import annotations

from namel3ss.runtime.memory_persist.render import (
    restore_failed_lines,
    restore_failed_title,
    wake_up_lines,
    wake_up_title,
)
from namel3ss.traces.builders import build_memory_restore_failed, build_memory_wake_up_report


def build_wake_up_report_event(
    *,
    project_id: str,
    restored: bool,
    total_items: int,
    team_items: int,
    active_rules: int,
    pending_proposals: int,
    pending_handoffs: int,
    cache_entries: int,
    cache_enabled: bool,
) -> dict:
    return build_memory_wake_up_report(
        project_id=project_id,
        title=wake_up_title(),
        lines=wake_up_lines(
            restored=restored,
            total_items=total_items,
            team_items=team_items,
            active_rules=active_rules,
            pending_proposals=pending_proposals,
            pending_handoffs=pending_handoffs,
            cache_entries=cache_entries,
            cache_enabled=cache_enabled,
        ),
    )


def build_restore_failed_event(*, project_id: str, reason: str, detail: str | None = None) -> dict:
    return build_memory_restore_failed(
        project_id=project_id,
        title=restore_failed_title(),
        lines=restore_failed_lines(reason=reason, detail=detail),
    )


__all__ = ["build_restore_failed_event", "build_wake_up_report_event"]
