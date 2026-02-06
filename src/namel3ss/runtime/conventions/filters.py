from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def parse_filter_param(raw: str, *, allowed_fields: tuple[str, ...], route_name: str) -> dict[str, str]:
    text = (raw or "").strip()
    if not text:
        return {}
    filters: dict[str, str] = {}
    for part in text.split(","):
        chunk = part.strip()
        if not chunk:
            continue
        if ":" not in chunk:
            raise Namel3ssError(_invalid_filter_message(route_name))
        field, value = chunk.split(":", 1)
        field = field.strip()
        value = value.strip()
        if not field or not value:
            raise Namel3ssError(_invalid_filter_message(route_name))
        if allowed_fields and field not in allowed_fields:
            raise Namel3ssError(_unknown_filter_field_message(route_name, field))
        filters[field] = value
    if not filters:
        return {}
    return filters


def apply_filters(response: dict, *, list_fields: tuple[str, ...], filters: dict[str, str]) -> dict:
    if not filters or not list_fields:
        return response
    updated = dict(response)
    for name in list_fields:
        items = updated.get(name)
        if not isinstance(items, list):
            continue
        updated[name] = _filter_items(items, filters)
    return updated


def _filter_items(items: list, filters: dict[str, str]) -> list:
    filtered: list = []
    for item in items:
        if not isinstance(item, dict):
            filtered.append(item)
            continue
        matches = True
        for key, value in filters.items():
            raw = item.get(key)
            if raw is None:
                matches = False
                break
            if str(raw) != value:
                matches = False
                break
        if matches:
            filtered.append(item)
    return filtered


def _invalid_filter_message(route_name: str) -> str:
    return build_guidance_message(
        what=f'Filter for route "{route_name}" is invalid.',
        why="Filters must use field:value pairs separated by commas.",
        fix="Provide filters like status:open,priority:high.",
        example="filter=status:open,priority:high",
    )


def _unknown_filter_field_message(route_name: str, field: str) -> str:
    return build_guidance_message(
        what=f'Filter field "{field}" is not allowed for route "{route_name}".',
        why="The filter field is not listed in conventions.",
        fix="Update conventions.yaml to allow the field or remove it.",
        example="filter=status:open",
    )


__all__ = ["apply_filters", "parse_filter_param"]
