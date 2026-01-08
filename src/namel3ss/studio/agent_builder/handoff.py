from __future__ import annotations

from namel3ss.ir import nodes as ir
from namel3ss.runtime.memory.api import MemoryManager
from namel3ss.runtime.memory_handoff import select_handoff_items
from namel3ss.runtime.memory_handoff.packet import build_packet_preview
from namel3ss.runtime.memory_lanes.context import resolve_team_id
from namel3ss.runtime.memory_lanes.model import LANE_TEAM, agent_lane_key
from namel3ss.runtime.memory_rules import active_rules_for_scope


def list_handoffs(memory_manager: MemoryManager, program: ir.Program) -> list[dict]:
    team_id = resolve_team_id(
        project_root=getattr(program, "project_root", None),
        app_path=getattr(program, "app_path", None),
        config=None,
    )
    memory_manager.ensure_restored(
        project_root=getattr(program, "project_root", None),
        app_path=getattr(program, "app_path", None),
    )
    space_ctx = memory_manager.space_context(
        {},
        project_root=getattr(program, "project_root", None),
        app_path=getattr(program, "app_path", None),
    )
    team_rules = active_rules_for_scope(semantic=memory_manager.semantic, space_ctx=space_ctx, scope="team")
    packets = memory_manager.handoffs.list_packets(team_id)
    data: list[dict] = []
    for packet in packets:
        packet_team_id = packet.team_id or team_id
        from_key = agent_lane_key(space_ctx, space=packet.space, agent_id=packet.from_agent_id)
        team_key = space_ctx.store_key_for(packet.space, lane=LANE_TEAM)
        selection = select_handoff_items(
            agent_items=memory_manager.semantic.items_for_store(from_key),
            team_items=memory_manager.semantic.items_for_store(team_key),
            proposals=memory_manager.agreements.list_pending(packet_team_id),
            rules=team_rules,
        )
        previews = build_packet_preview(
            short_term=memory_manager.short_term,
            semantic=memory_manager.semantic,
            profile=memory_manager.profile,
            item_ids=list(packet.items),
            reasons=selection.reasons,
        )
        data.append(
            {
                "packet_id": packet.packet_id,
                "status": packet.status,
                "from_agent_id": packet.from_agent_id,
                "to_agent_id": packet.to_agent_id,
                "phase_id": packet.phase_id,
                "summary_lines": list(packet.summary_lines),
                "previews": previews,
            }
        )
    return data


__all__ = ["list_handoffs"]
