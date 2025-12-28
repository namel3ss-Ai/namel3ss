from __future__ import annotations

from typing import Optional, TypedDict

LINK_TYPE_DEPENDS_ON = "depends_on"
LINK_TYPE_CAUSED_BY = "caused_by"
LINK_TYPE_REPLACED = "replaced"
LINK_TYPE_PROMOTED_FROM = "promoted_from"
LINK_TYPE_CONFLICTS_WITH = "conflicts_with"
LINK_TYPE_SUPPORTS = "supports"

LINK_TYPES = {
    LINK_TYPE_DEPENDS_ON,
    LINK_TYPE_CAUSED_BY,
    LINK_TYPE_REPLACED,
    LINK_TYPE_PROMOTED_FROM,
    LINK_TYPE_CONFLICTS_WITH,
    LINK_TYPE_SUPPORTS,
}

LINK_ORDER = [
    LINK_TYPE_REPLACED,
    LINK_TYPE_PROMOTED_FROM,
    LINK_TYPE_CONFLICTS_WITH,
    LINK_TYPE_CAUSED_BY,
    LINK_TYPE_DEPENDS_ON,
    LINK_TYPE_SUPPORTS,
]

LINK_LIMIT = 10


class LinkRecord(TypedDict, total=False):
    type: str
    to_id: str
    reason_code: str
    created_in_phase_id: str
    source_event_id: Optional[str]


def link_sort_key(link: LinkRecord) -> tuple[int, str, str]:
    link_type = link.get("type") or ""
    try:
        rank = LINK_ORDER.index(link_type)
    except ValueError:
        rank = len(LINK_ORDER)
    return (rank, str(link.get("to_id") or ""), str(link.get("reason_code") or ""))


__all__ = [
    "LINK_LIMIT",
    "LINK_ORDER",
    "LINK_TYPE_CAUSED_BY",
    "LINK_TYPE_CONFLICTS_WITH",
    "LINK_TYPE_DEPENDS_ON",
    "LINK_TYPE_PROMOTED_FROM",
    "LINK_TYPE_REPLACED",
    "LINK_TYPE_SUPPORTS",
    "LINK_TYPES",
    "LinkRecord",
    "link_sort_key",
]
