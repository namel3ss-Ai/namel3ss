from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.runtime.auth.route_permissions import RouteRequirement


@dataclass(frozen=True)
class RouteEntry:
    name: str
    method: str
    path: str
    flow_name: str
    upload: bool
    parameters: dict[str, ir.RouteField]
    request: dict[str, ir.RouteField] | None
    response: dict[str, ir.RouteField]
    segments: tuple[str, ...]
    param_names: tuple[str, ...]
    requires: RouteRequirement | None = None


@dataclass(frozen=True)
class RouteMatch:
    entry: RouteEntry
    path_params: dict[str, str]


class RouteRegistry:
    def __init__(self) -> None:
        self._routes: list[RouteEntry] = []
        self._signatures: dict[str, tuple] = {}
        self._revision: str | None = None

    def update(
        self,
        routes: Iterable[ir.RouteDefinition],
        *,
        revision: str | None = None,
        requirements: dict[str, RouteRequirement] | None = None,
    ) -> dict[str, list[str]]:
        if revision is not None and revision == self._revision:
            return {"added": [], "removed": [], "updated": []}
        new_entries = _build_entries(routes, requirements=requirements or {})
        diff = _diff_routes(self._signatures, new_entries)
        self._routes = new_entries
        self._signatures = {entry.name: _signature(entry) for entry in new_entries}
        self._revision = revision
        return diff

    def match(self, method: str, path: str) -> RouteMatch | None:
        if not self._routes:
            return None
        normalized = _normalize_path(path)
        for entry in self._routes:
            if entry.method != method:
                continue
            match = _match_entry(entry, normalized)
            if match is not None:
                return match
        return None

    @property
    def routes(self) -> list[RouteEntry]:
        return list(self._routes)


def _build_entries(routes: Iterable[ir.RouteDefinition], *, requirements: dict[str, RouteRequirement]) -> list[RouteEntry]:
    seen_paths: set[tuple[str, str]] = set()
    entries: list[RouteEntry] = []
    for route in routes:
        name = str(route.name or "")
        method = str(route.method or "").upper()
        path = _normalize_path(str(route.path or ""))
        if not name or not method or not path:
            continue
        key = (method, path)
        if key in seen_paths:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Route '{name}' duplicates {method} {path}.",
                    why="Every route must have a unique method and path.",
                    fix="Rename the route or change its method/path.",
                    example='route "unique_route":\n  path is "/api/unique"\n  method is "GET"',
                ),
                line=route.line,
                column=route.column,
            )
        seen_paths.add(key)
        segments, param_names = _compile_path(path)
        requirement = requirements.get(name)
        entries.append(
            RouteEntry(
                name=name,
                method=method,
                path=path,
                flow_name=str(route.flow_name or ""),
                upload=bool(route.upload),
                parameters=dict(route.parameters or {}),
                request=dict(route.request) if route.request else None,
                response=dict(route.response or {}),
                segments=segments,
                param_names=param_names,
                requires=requirement,
            )
        )
    return sorted(entries, key=lambda entry: entry.name)


def _normalize_path(path: str) -> str:
    if not path:
        return "/"
    value = path if path.startswith("/") else f"/{path}"
    if value != "/" and value.endswith("/"):
        value = value[:-1]
    return value


def _compile_path(path: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    segments = tuple(seg for seg in path.split("/") if seg)
    params: list[str] = []
    for segment in segments:
        if segment.startswith("{") and segment.endswith("}"):
            name = segment[1:-1].strip()
            params.append(name or segment)
    return segments, tuple(params)


def _match_entry(entry: RouteEntry, path: str) -> RouteMatch | None:
    parts = tuple(seg for seg in path.split("/") if seg)
    if len(parts) != len(entry.segments):
        return None
    params: dict[str, str] = {}
    for expected, actual in zip(entry.segments, parts):
        if expected.startswith("{") and expected.endswith("}"):
            key = expected[1:-1].strip()
            params[key] = actual
            continue
        if expected != actual:
            return None
    return RouteMatch(entry=entry, path_params=params)


def _signature(entry: RouteEntry) -> tuple:
    return (
        entry.method,
        entry.path,
        entry.flow_name,
        entry.upload,
        _field_signature(entry.parameters),
        _field_signature(entry.request),
        _field_signature(entry.response),
        _requires_signature(entry.requires),
    )


def _field_signature(fields: dict[str, ir.RouteField] | None) -> tuple:
    if not fields:
        return ()
    return tuple(sorted((name, field.type_name) for name, field in fields.items()))


def _requires_signature(requirement: RouteRequirement | None) -> tuple:
    if requirement is None:
        return ()
    return (tuple(requirement.roles), tuple(requirement.permissions))


def _diff_routes(old: dict[str, tuple], entries: list[RouteEntry]) -> dict[str, list[str]]:
    new_signatures = {entry.name: _signature(entry) for entry in entries}
    added = [name for name in new_signatures.keys() if name not in old]
    removed = [name for name in old.keys() if name not in new_signatures]
    updated = [name for name, sig in new_signatures.items() if old.get(name) and old.get(name) != sig]
    return {
        "added": sorted(added),
        "removed": sorted(removed),
        "updated": sorted(updated),
    }


__all__ = ["RouteEntry", "RouteMatch", "RouteRegistry"]
