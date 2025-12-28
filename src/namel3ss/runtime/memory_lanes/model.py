from __future__ import annotations

from typing import Mapping

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.memory.spaces import (
    SPACE_PROJECT,
    SPACE_SESSION,
    SPACE_SYSTEM,
    SPACE_USER,
    SpaceContext,
    normalize_owner,
    store_key,
)


LANE_MY = "my"
LANE_TEAM = "team"
LANE_SYSTEM = "system"
LANE_AGENT = "agent"

LANES = {LANE_MY, LANE_TEAM, LANE_SYSTEM, LANE_AGENT}

VISIBLE_ME = "me"
VISIBLE_TEAM = "team"
VISIBLE_ALL = "all"

VISIBILITY = {VISIBLE_ME, VISIBLE_TEAM, VISIBLE_ALL}

LANE_BY_SPACE = {
    SPACE_SESSION: [LANE_MY],
    SPACE_USER: [LANE_MY],
    SPACE_PROJECT: [LANE_TEAM, LANE_AGENT],
    SPACE_SYSTEM: [LANE_SYSTEM],
}


def lane_visibility(lane: str) -> str:
    if lane == LANE_TEAM:
        return VISIBLE_TEAM
    if lane == LANE_SYSTEM:
        return VISIBLE_ALL
    return VISIBLE_ME


def lane_can_change(lane: str, *, allow_team_change: bool = True) -> bool:
    if lane == LANE_SYSTEM:
        return False
    if lane == LANE_TEAM:
        return bool(allow_team_change)
    return True


def lane_for_space(space: str) -> str:
    allowed = LANE_BY_SPACE.get(space)
    if allowed:
        return allowed[0]
    return LANE_MY


def lanes_for_space(space: str, *, read_order: list[str] | None = None) -> list[str]:
    allowed = set(LANE_BY_SPACE.get(space, [LANE_MY]))
    order = read_order or [LANE_MY, LANE_TEAM, LANE_SYSTEM]
    return [lane for lane in order if lane in allowed]


def lane_allowed_in_space(space: str, lane: str) -> bool:
    return lane in LANE_BY_SPACE.get(space, [LANE_MY])


def ensure_lane_meta(
    meta: Mapping[str, object] | None,
    *,
    lane: str,
    visible_to: str | None = None,
    can_change: bool | None = None,
    allow_team_change: bool = True,
    agent_id: str | None = None,
) -> dict:
    payload = dict(meta or {})
    payload.setdefault("lane", lane)
    payload.setdefault("visible_to", visible_to or lane_visibility(lane))
    if can_change is None:
        payload.setdefault("can_change", lane_can_change(lane, allow_team_change=allow_team_change))
    else:
        payload.setdefault("can_change", bool(can_change))
    if lane == LANE_AGENT:
        if agent_id:
            payload["agent_id"] = str(agent_id)
    return payload


def validate_lane_rules(item: object) -> tuple[str, str, bool]:
    meta = {}
    if hasattr(item, "meta"):
        meta = getattr(item, "meta") or {}
    elif isinstance(item, dict):
        meta = item.get("meta") or {}
    lane = meta.get("lane")
    visible_to = meta.get("visible_to")
    can_change = meta.get("can_change")
    if lane not in LANES:
        raise Namel3ssError(
            "Invalid memory lane. Expected one of: my, team, system, agent.",
            details={"lane": lane},
        )
    if lane == LANE_AGENT:
        agent_id = meta.get("agent_id")
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise Namel3ssError(
                "Agent lane items must include agent_id.",
                details={"agent_id": agent_id},
            )
    if visible_to not in VISIBILITY:
        raise Namel3ssError(
            "Memory visible_to must be one of: me, team, all.",
            details={"visible_to": visible_to},
        )
    if not isinstance(can_change, bool):
        raise Namel3ssError(
            "Memory can_change must be true or false.",
            details={"can_change": can_change},
        )
    if lane == LANE_SYSTEM and can_change:
        raise Namel3ssError(
            "System lane items cannot be changed.",
            details={"lane": lane},
        )
    return lane, visible_to, can_change


def is_agent_lane_item(item: object) -> bool:
    meta = {}
    if hasattr(item, "meta"):
        meta = getattr(item, "meta") or {}
    elif isinstance(item, dict):
        meta = item.get("meta") or {}
    if meta.get("lane") != LANE_AGENT:
        return False
    agent_id = meta.get("agent_id")
    return isinstance(agent_id, str) and bool(agent_id.strip())


def agent_lane_key(space_ctx: SpaceContext, *, space: str, agent_id: str) -> str:
    if not isinstance(agent_id, str) or not agent_id.strip():
        raise Namel3ssError("Agent id is required for agent lane.")
    lane = f"{LANE_AGENT}:{normalize_owner(agent_id, default='agent')}"
    return store_key(space, space_ctx.owner_for(space), lane)


__all__ = [
    "LANE_BY_SPACE",
    "LANE_AGENT",
    "LANE_MY",
    "LANE_SYSTEM",
    "LANE_TEAM",
    "LANES",
    "VISIBLE_ALL",
    "VISIBLE_ME",
    "VISIBLE_TEAM",
    "VISIBILITY",
    "agent_lane_key",
    "ensure_lane_meta",
    "is_agent_lane_item",
    "lane_allowed_in_space",
    "lane_can_change",
    "lane_for_space",
    "lane_visibility",
    "lanes_for_space",
    "validate_lane_rules",
]
