from __future__ import annotations

from namel3ss.runtime.memory.contract import MemoryItem
from namel3ss.runtime.memory_lanes.model import LANE_MY
from namel3ss.runtime.memory_links import (
    LINK_TYPE_CAUSED_BY,
    LinkTracker,
    build_link_record,
    build_preview_for_tool,
    link_lines,
    path_lines,
)
from namel3ss.traces.builders import build_memory_links, build_memory_path

from .utils import _phase_id_for_item


def _build_link_events(*, ai_profile: str, session: str, items: list[MemoryItem]) -> list[dict]:
    events: list[dict] = []
    ordered = sorted(items, key=lambda item: item.id)
    for item in ordered:
        links = item.meta.get("links")
        link_count = len(links) if isinstance(links, list) else 0
        if link_count <= 0:
            continue
        phase_id = _phase_id_for_item(item, "phase-unknown")
        space = item.meta.get("space", "session")
        owner = item.meta.get("owner", "anonymous")
        lane = item.meta.get("lane", LANE_MY)
        events.append(
            build_memory_links(
                ai_profile=ai_profile,
                session=session,
                memory_id=item.id,
                phase_id=phase_id,
                space=space,
                owner=owner,
                link_count=link_count,
                lines=link_lines(item),
                lane=lane,
            )
        )
        events.append(
            build_memory_path(
                ai_profile=ai_profile,
                session=session,
                memory_id=item.id,
                phase_id=phase_id,
                space=space,
                owner=owner,
                title="Memory path",
                lines=path_lines(item),
                lane=lane,
            )
        )
    return events


def _link_tool_events(
    link_tracker: LinkTracker,
    item: MemoryItem,
    tool_events: list[dict],
    *,
    fallback_phase: str,
) -> None:
    if not tool_events:
        return
    phase_id = _phase_id_for_item(item, fallback_phase)
    for entry in tool_events:
        if entry.get("type") != "call":
            continue
        tool_call_id = entry.get("tool_call_id")
        if not tool_call_id:
            continue
        tool_name = entry.get("name") or "tool"
        link_tracker.add_link(
            from_id=item.id,
            link=build_link_record(
                link_type=LINK_TYPE_CAUSED_BY,
                to_id=str(tool_call_id),
                reason_code="tool_call",
                created_in_phase_id=phase_id,
                source_event_id=str(tool_call_id),
            ),
            preview=build_preview_for_tool(str(tool_name)),
        )
