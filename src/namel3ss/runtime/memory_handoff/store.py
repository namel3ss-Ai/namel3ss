from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from namel3ss.runtime.memory_handoff.model import (
    HANDOFF_STATUS_APPLIED,
    HANDOFF_STATUS_PENDING,
    HANDOFF_STATUS_REJECTED,
    HandoffPacket,
)


class HandoffStore:
    def __init__(self) -> None:
        self._counter = 0
        self._tick = 0
        self._by_id: dict[str, HandoffPacket] = {}
        self._by_team: dict[str, dict[str, list[HandoffPacket]]] = {}

    def create_packet(
        self,
        *,
        from_agent_id: str,
        to_agent_id: str,
        team_id: str,
        space: str,
        phase_id: str,
        created_by: str,
        items: list[str],
        summary_lines: list[str],
    ) -> HandoffPacket:
        packet_id = self._next_id()
        created_at = self._next_tick()
        packet = HandoffPacket(
            packet_id=packet_id,
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            team_id=team_id,
            space=space,
            phase_id=phase_id,
            created_by=created_by,
            created_at=created_at,
            items=list(items),
            summary_lines=list(summary_lines),
            status=HANDOFF_STATUS_PENDING,
        )
        self._by_id[packet_id] = packet
        team_phases = self._by_team.setdefault(team_id, {})
        team_phases.setdefault(phase_id, []).append(packet)
        return packet

    def list_packets(self, team_id: str, *, phase_id: str | None = None) -> list[HandoffPacket]:
        packets: list[HandoffPacket] = []
        if phase_id is None:
            for entries in self._by_team.get(team_id, {}).values():
                packets.extend(entries)
        else:
            packets.extend(self._by_team.get(team_id, {}).get(phase_id, []))
        packets.sort(key=lambda packet: (packet.created_at, packet.packet_id))
        return packets

    def get_packet(self, packet_id: str) -> HandoffPacket | None:
        return self._by_id.get(packet_id)

    def apply_packet(self, packet_id: str) -> HandoffPacket | None:
        return self._update_status(packet_id, HANDOFF_STATUS_APPLIED)

    def reject_packet(self, packet_id: str) -> HandoffPacket | None:
        return self._update_status(packet_id, HANDOFF_STATUS_REJECTED)

    def _update_status(self, packet_id: str, status: str) -> HandoffPacket | None:
        packet = self._by_id.get(packet_id)
        if packet is None:
            return None
        if packet.status == status:
            return packet
        updated = replace(packet, status=status)
        self._by_id[packet_id] = updated
        self._replace_packet(updated)
        return updated

    def _replace_packet(self, packet: HandoffPacket) -> None:
        team_phases = self._by_team.get(packet.team_id, {})
        entries = team_phases.get(packet.phase_id, [])
        replaced: list[HandoffPacket] = []
        for entry in entries:
            if entry.packet_id == packet.packet_id:
                replaced.append(packet)
            else:
                replaced.append(entry)
        team_phases[packet.phase_id] = replaced

    def _next_id(self) -> str:
        self._counter += 1
        return f"handoff-{self._counter}"

    def _next_tick(self) -> int:
        self._tick += 1
        return self._tick


__all__ = ["HandoffStore"]
