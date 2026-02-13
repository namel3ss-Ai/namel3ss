from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.router.messages import format_not_allowed_message
from namel3ss.runtime.router.registry import RouteEntry


def format_flow_response(entry: RouteEntry, value: object) -> dict:
    if isinstance(value, dict):
        return value
    response_fields = list(entry.response.keys()) if entry.response else []
    if len(response_fields) == 1:
        return {response_fields[0]: value}
    if not response_fields:
        return {"result": value}
    raise Namel3ssError("Flow response must be an object matching the route response schema.")


def list_response_fields(fields: dict) -> tuple[str, ...]:
    if not fields:
        return ()
    names: list[str] = []
    for name, field in fields.items():
        type_name = getattr(field, "type_name", "")
        if isinstance(type_name, str) and type_name.startswith("list<"):
            names.append(name)
    return tuple(sorted(names))


def resolve_response_format(route_name: str, query: dict[str, str], headers: dict[str, str], formats) -> str:
    requested = None
    if "format" in query:
        requested = str(query.get("format") or "").strip().lower()
    if not requested:
        accept = headers.get("Accept") or headers.get("accept") or ""
        lowered = accept.lower()
        if "toon" in lowered:
            requested = "toon"
    if not requested:
        requested = "json"
    allowed = formats.formats_for_route(route_name)
    if requested not in allowed:
        raise Namel3ssError(
            format_not_allowed_message(route_name, requested),
            details={"http_status": 406, "category": "format", "reason_code": "format_not_allowed"},
        )
    return requested


__all__ = ["format_flow_response", "list_response_fields", "resolve_response_format"]
