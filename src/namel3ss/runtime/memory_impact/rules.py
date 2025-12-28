from __future__ import annotations

from namel3ss.runtime.memory_links.model import (
    LINK_TYPE_CAUSED_BY,
    LINK_TYPE_CONFLICTS_WITH,
    LINK_TYPE_DEPENDS_ON,
    LINK_TYPE_PROMOTED_FROM,
    LINK_TYPE_REPLACED,
    LINK_TYPE_SUPPORTS,
)

SPACE_PRIORITY = ["session", "user", "project", "system"]

IMPACT_LINK_TYPES = {
    LINK_TYPE_DEPENDS_ON,
    LINK_TYPE_CAUSED_BY,
    LINK_TYPE_SUPPORTS,
    LINK_TYPE_CONFLICTS_WITH,
    LINK_TYPE_REPLACED,
    LINK_TYPE_PROMOTED_FROM,
}

REVERSE_LINK_TYPES = {
    LINK_TYPE_DEPENDS_ON,
    LINK_TYPE_SUPPORTS,
    LINK_TYPE_CAUSED_BY,
}

FORWARD_LINK_TYPES = {
    LINK_TYPE_REPLACED,
    LINK_TYPE_PROMOTED_FROM,
}

BIDIRECTIONAL_LINK_TYPES = {
    LINK_TYPE_CONFLICTS_WITH,
}


def link_direction(link_type: str) -> str:
    if link_type in FORWARD_LINK_TYPES:
        return "forward"
    if link_type in REVERSE_LINK_TYPES:
        return "reverse"
    if link_type in BIDIRECTIONAL_LINK_TYPES:
        return "both"
    return "skip"


def phase_index(phase_id: str) -> int:
    if isinstance(phase_id, str) and phase_id.startswith("phase-"):
        suffix = phase_id.split("-", 1)[1]
        if suffix.isdigit():
            return int(suffix)
    return 10_000


def space_rank(space: str) -> int:
    try:
        return SPACE_PRIORITY.index(space)
    except ValueError:
        return len(SPACE_PRIORITY)


def impact_sort_key(phase_id: str, space: str, memory_id: str) -> tuple[int, int, str]:
    return (phase_index(str(phase_id)), space_rank(str(space)), str(memory_id))


__all__ = [
    "BIDIRECTIONAL_LINK_TYPES",
    "FORWARD_LINK_TYPES",
    "IMPACT_LINK_TYPES",
    "REVERSE_LINK_TYPES",
    "SPACE_PRIORITY",
    "impact_sort_key",
    "link_direction",
    "phase_index",
    "space_rank",
]
