from __future__ import annotations

from namel3ss.traces.builders import build_memory_cache_hit, build_memory_cache_miss


def build_cache_event(
    *,
    ai_profile: str,
    session: str,
    space: str,
    lane: str,
    phase_id: str,
    hit: bool,
) -> dict:
    title, lines = _cache_lines(hit)
    if hit:
        return build_memory_cache_hit(
            ai_profile=ai_profile,
            session=session,
            space=space,
            lane=lane,
            phase_id=phase_id,
            title=title,
            lines=lines,
        )
    return build_memory_cache_miss(
        ai_profile=ai_profile,
        session=session,
        space=space,
        lane=lane,
        phase_id=phase_id,
        title=title,
        lines=lines,
    )


def _cache_lines(hit: bool) -> tuple[str, list[str]]:
    if hit:
        return "Memory cache hit", ["Cache was used for recall.", "Cached result was returned."]
    return "Memory cache miss", ["Cache was not used for recall.", "Result was stored for reuse."]


__all__ = ["build_cache_event"]
