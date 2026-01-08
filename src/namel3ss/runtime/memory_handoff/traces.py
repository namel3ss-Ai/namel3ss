from __future__ import annotations

from namel3ss.runtime.memory_handoff.model import HandoffPacket
from namel3ss.runtime.memory_handoff.render import diff_lines as handoff_diff_lines
from namel3ss.traces.builders import (
    build_memory_agent_briefing,
    build_memory_handoff_applied,
    build_memory_handoff_created,
    build_memory_handoff_rejected,
)


def build_handoff_created_event(*, ai_profile: str, session: str, packet: HandoffPacket) -> dict:
    return build_memory_handoff_created(
        ai_profile=ai_profile,
        session=session,
        packet_id=packet.packet_id,
        from_agent_id=packet.from_agent_id,
        to_agent_id=packet.to_agent_id,
        team_id=packet.team_id,
        phase_id=packet.phase_id,
        title="Memory handoff created",
        lines=_created_lines(packet),
    )


def build_handoff_applied_event(
    *,
    ai_profile: str,
    session: str,
    packet: HandoffPacket,
    item_count: int,
    applied_items: list | None = None,
) -> dict:
    diff_lines = handoff_diff_lines(applied_items) if applied_items is not None else None
    return build_memory_handoff_applied(
        ai_profile=ai_profile,
        session=session,
        packet_id=packet.packet_id,
        from_agent_id=packet.from_agent_id,
        to_agent_id=packet.to_agent_id,
        item_count=item_count,
        title="Memory handoff applied",
        lines=_applied_lines(packet, item_count=item_count, diff_lines=diff_lines),
    )


def build_handoff_rejected_event(*, ai_profile: str, session: str, packet: HandoffPacket) -> dict:
    return build_memory_handoff_rejected(
        ai_profile=ai_profile,
        session=session,
        packet_id=packet.packet_id,
        from_agent_id=packet.from_agent_id,
        to_agent_id=packet.to_agent_id,
        title="Memory handoff rejected",
        lines=_rejected_lines(packet),
    )


def build_agent_briefing_event(*, ai_profile: str, session: str, packet: HandoffPacket) -> dict:
    lines = list(packet.summary_lines) if packet.summary_lines else ["No briefing is available."]
    return build_memory_agent_briefing(
        ai_profile=ai_profile,
        session=session,
        packet_id=packet.packet_id,
        to_agent_id=packet.to_agent_id,
        title="Agent briefing",
        lines=lines,
    )


def _created_lines(packet: HandoffPacket) -> list[str]:
    return [
        "Handoff packet created.",
        f"Packet id is {packet.packet_id}.",
        f"From agent is {packet.from_agent_id}.",
        f"To agent is {packet.to_agent_id}.",
        f"Item count is {len(packet.items)}.",
    ]


def _applied_lines(packet: HandoffPacket, *, item_count: int, diff_lines: list[str] | None = None) -> list[str]:
    lines = [
        "Handoff packet applied.",
        f"Packet id is {packet.packet_id}.",
        f"From agent is {packet.from_agent_id}.",
        f"To agent is {packet.to_agent_id}.",
        f"Item count is {int(item_count)}.",
    ]
    if diff_lines:
        lines.extend(diff_lines)
    return lines


def _rejected_lines(packet: HandoffPacket) -> list[str]:
    return [
        "Handoff packet rejected.",
        f"Packet id is {packet.packet_id}.",
        f"From agent is {packet.from_agent_id}.",
        f"To agent is {packet.to_agent_id}.",
    ]


__all__ = [
    "build_agent_briefing_event",
    "build_handoff_applied_event",
    "build_handoff_created_event",
    "build_handoff_rejected_event",
]
