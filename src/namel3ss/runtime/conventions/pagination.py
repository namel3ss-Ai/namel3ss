from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.conventions.config import RouteConventions


def parse_pagination(
    query: dict[str, str],
    *,
    conventions: RouteConventions,
    route_name: str,
) -> tuple[int, int]:
    page = _parse_int(query.get("page"), default=1)
    page_size = _parse_int(query.get("page_size"), default=conventions.page_size_default)
    if page < 1:
        raise Namel3ssError(_pagination_message(route_name, "page"))
    if page_size < 1:
        raise Namel3ssError(_pagination_message(route_name, "page_size"))
    if page_size > conventions.page_size_max:
        raise Namel3ssError(_page_size_max_message(route_name, conventions.page_size_max))
    return page, page_size


def apply_pagination(
    response: dict,
    *,
    list_fields: tuple[str, ...],
    page: int,
    page_size: int,
) -> tuple[dict, bool]:
    if not list_fields:
        return response, False
    updated = dict(response)
    start = (page - 1) * page_size
    end = start + page_size
    has_more = False
    for name in list_fields:
        items = updated.get(name)
        if not isinstance(items, list):
            continue
        if len(items) > end:
            has_more = True
        updated[name] = items[start:end]
    return updated, has_more


def _parse_int(value: str | None, *, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except Exception:
        return default


def _pagination_message(route_name: str, field: str) -> str:
    return build_guidance_message(
        what=f'Pagination "{field}" is invalid for route "{route_name}".',
        why="Pagination values must be positive integers.",
        fix=f"Provide {field} as a positive integer.",
        example=f"{field}=1",
    )


def _page_size_max_message(route_name: str, limit: int) -> str:
    return build_guidance_message(
        what=f'Pagination "page_size" exceeds the limit for route "{route_name}".',
        why=f"page_size must be less than or equal to {limit}.",
        fix="Use a smaller page_size value.",
        example="page_size=50",
    )


__all__ = ["apply_pagination", "parse_pagination"]
