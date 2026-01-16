from __future__ import annotations

from namel3ss.utils.slugify import slugify_text


def agent_id_from_name(name: str) -> str:
    slug = slugify_text(name)
    return slug or "agent"


def team_id_from_agent_ids(agent_ids: list[str]) -> str:
    base = slugify_text("_".join(agent_ids))
    if not base:
        return "team"
    return f"team_{base}"


__all__ = ["agent_id_from_name", "team_id_from_agent_ids"]
