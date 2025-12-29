from __future__ import annotations

from namel3ss.traces.schema import TRACE_VERSION, TraceEventType


def build_memory_explanation(
    *,
    for_event_index: int,
    title: str,
    lines: list[str],
    related_ids: list[str] | None = None,
) -> dict:
    event = {
        "type": TraceEventType.MEMORY_EXPLANATION,
        "trace_version": TRACE_VERSION,
        "for_event_index": int(for_event_index),
        "title": title,
        "lines": list(lines),
    }
    if related_ids:
        event["related_ids"] = list(related_ids)
    return event


def build_memory_links(
    *,
    ai_profile: str,
    session: str,
    memory_id: str,
    phase_id: str,
    space: str,
    owner: str,
    link_count: int,
    lines: list[str],
    lane: str | None = None,
) -> dict:
    event = {
        "type": TraceEventType.MEMORY_LINKS,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "memory_id": memory_id,
        "phase_id": phase_id,
        "space": space,
        "owner": owner,
        "link_count": int(link_count),
        "lines": list(lines),
    }
    if lane is not None:
        event["lane"] = lane
    return event


def build_memory_path(
    *,
    ai_profile: str,
    session: str,
    memory_id: str,
    phase_id: str,
    space: str,
    owner: str,
    title: str,
    lines: list[str],
    lane: str | None = None,
) -> dict:
    event = {
        "type": TraceEventType.MEMORY_PATH,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "memory_id": memory_id,
        "phase_id": phase_id,
        "space": space,
        "owner": owner,
        "title": title,
        "lines": list(lines),
    }
    if lane is not None:
        event["lane"] = lane
    return event


def build_memory_impact(
    *,
    ai_profile: str,
    session: str,
    memory_id: str,
    space: str,
    owner: str,
    phase_id: str,
    depth_used: int,
    item_count: int,
    title: str,
    lines: list[str],
    path_lines: list[str] | None = None,
    lane: str | None = None,
) -> dict:
    event = {
        "type": TraceEventType.MEMORY_IMPACT,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "memory_id": memory_id,
        "space": space,
        "owner": owner,
        "phase_id": phase_id,
        "depth_used": int(depth_used),
        "item_count": int(item_count),
        "title": title,
        "lines": list(lines),
    }
    if path_lines is not None:
        event["path_lines"] = list(path_lines)
    if lane is not None:
        event["lane"] = lane
    return event


def build_memory_change_preview(
    *,
    ai_profile: str,
    session: str,
    memory_id: str,
    change_kind: str,
    title: str,
    lines: list[str],
    space: str | None = None,
    owner: str | None = None,
    phase_id: str | None = None,
    lane: str | None = None,
) -> dict:
    event = {
        "type": TraceEventType.MEMORY_CHANGE_PREVIEW,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "memory_id": memory_id,
        "change_kind": change_kind,
        "title": title,
        "lines": list(lines),
    }
    if space is not None:
        event["space"] = space
    if owner is not None:
        event["owner"] = owner
    if phase_id is not None:
        event["phase_id"] = phase_id
    if lane is not None:
        event["lane"] = lane
    return event


def build_memory_budget(
    *,
    ai_profile: str,
    session: str,
    space: str,
    lane: str,
    phase_id: str,
    owner: str,
    title: str,
    lines: list[str],
) -> dict:
    return {
        "type": TraceEventType.MEMORY_BUDGET,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "space": space,
        "lane": lane,
        "phase_id": phase_id,
        "owner": owner,
        "title": title,
        "lines": list(lines),
    }


def build_memory_compaction(
    *,
    ai_profile: str,
    session: str,
    space: str,
    lane: str,
    phase_id: str,
    owner: str,
    action: str,
    items_removed_count: int,
    summary_written: bool,
    reason: str,
    title: str,
    lines: list[str],
) -> dict:
    return {
        "type": TraceEventType.MEMORY_COMPACTION,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "space": space,
        "lane": lane,
        "phase_id": phase_id,
        "owner": owner,
        "action": action,
        "items_removed_count": int(items_removed_count),
        "summary_written": bool(summary_written),
        "reason": reason,
        "title": title,
        "lines": list(lines),
    }


def build_memory_cache_hit(
    *,
    ai_profile: str,
    session: str,
    space: str,
    lane: str,
    phase_id: str,
    title: str,
    lines: list[str],
) -> dict:
    return {
        "type": TraceEventType.MEMORY_CACHE_HIT,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "space": space,
        "lane": lane,
        "phase_id": phase_id,
        "title": title,
        "lines": list(lines),
    }


def build_memory_cache_miss(
    *,
    ai_profile: str,
    session: str,
    space: str,
    lane: str,
    phase_id: str,
    title: str,
    lines: list[str],
) -> dict:
    return {
        "type": TraceEventType.MEMORY_CACHE_MISS,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "space": space,
        "lane": lane,
        "phase_id": phase_id,
        "title": title,
        "lines": list(lines),
    }


def build_memory_wake_up_report(
    *,
    project_id: str,
    title: str,
    lines: list[str],
) -> dict:
    return {
        "type": TraceEventType.MEMORY_WAKE_UP_REPORT,
        "trace_version": TRACE_VERSION,
        "project_id": project_id,
        "title": title,
        "lines": list(lines),
    }


def build_memory_restore_failed(
    *,
    project_id: str,
    title: str,
    lines: list[str],
) -> dict:
    return {
        "type": TraceEventType.MEMORY_RESTORE_FAILED,
        "trace_version": TRACE_VERSION,
        "project_id": project_id,
        "title": title,
        "lines": list(lines),
    }


def build_memory_pack_loaded(
    *,
    pack_id: str,
    pack_version: str,
    title: str,
    lines: list[str],
) -> dict:
    return {
        "type": TraceEventType.MEMORY_PACK_LOADED,
        "trace_version": TRACE_VERSION,
        "pack_id": pack_id,
        "pack_version": pack_version,
        "title": title,
        "lines": list(lines),
    }


def build_memory_pack_merged(
    *,
    title: str,
    lines: list[str],
) -> dict:
    return {
        "type": TraceEventType.MEMORY_PACK_MERGED,
        "trace_version": TRACE_VERSION,
        "title": title,
        "lines": list(lines),
    }


def build_memory_pack_overrides(
    *,
    title: str,
    lines: list[str],
) -> dict:
    return {
        "type": TraceEventType.MEMORY_PACK_OVERRIDES,
        "trace_version": TRACE_VERSION,
        "title": title,
        "lines": list(lines),
    }
