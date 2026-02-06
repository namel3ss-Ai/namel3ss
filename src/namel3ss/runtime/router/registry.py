from __future__ import annotations

from dataclasses import dataclass
import threading
from typing import Iterable

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.runtime.auth.route_permissions import RouteRequirement
from namel3ss.versioning.semver import version_sort_key


@dataclass(frozen=True)
class RouteEntry:
    name: str
    entity_name: str
    version: str | None
    status: str
    replacement: str | None
    deprecation_date: str | None
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
        self._lock = threading.RLock()

    def update(
        self,
        routes: Iterable[ir.RouteDefinition],
        *,
        revision: str | None = None,
        requirements: dict[str, RouteRequirement] | None = None,
        route_version_meta: dict[str, dict[str, object]] | None = None,
    ) -> dict[str, list[str]]:
        with self._lock:
            if revision is not None and revision == self._revision:
                return {"added": [], "removed": [], "updated": []}
            new_entries = _build_entries(
                routes,
                requirements=requirements or {},
                route_version_meta=route_version_meta or {},
            )
            diff = _diff_routes(self._signatures, new_entries)
            self._routes = new_entries
            self._signatures = {entry.name: _signature(entry) for entry in new_entries}
            self._revision = revision
            return diff

    def match(self, method: str, path: str, *, requested_version: str | None = None) -> RouteMatch | None:
        with self._lock:
            if not self._routes:
                return None
            normalized = _normalize_path(path)
            candidates: list[RouteMatch] = []
            for entry in self._routes:
                if entry.method != method:
                    continue
                match = _match_entry(entry, normalized)
                if match is not None:
                    candidates.append(match)
            if not candidates:
                return None
            selected = _select_match(candidates, requested_version=requested_version)
            return selected

    def removed_version(self, method: str, path: str, requested_version: str) -> RouteEntry | None:
        with self._lock:
            if not self._routes:
                return None
            normalized = _normalize_path(path)
            for entry in self._routes:
                if entry.method != method:
                    continue
                if entry.status != "removed":
                    continue
                if (entry.version or "") != requested_version:
                    continue
                if _match_entry(entry, normalized) is not None:
                    return entry
            return None

    @property
    def routes(self) -> list[RouteEntry]:
        with self._lock:
            return list(self._routes)


def _build_entries(
    routes: Iterable[ir.RouteDefinition],
    *,
    requirements: dict[str, RouteRequirement],
    route_version_meta: dict[str, dict[str, object]],
) -> list[RouteEntry]:
    seen_paths: dict[tuple[str, str], dict[str, str]] = {}
    entries: list[RouteEntry] = []
    for route in routes:
        name = str(route.name or "")
        method = str(route.method or "").upper()
        path = _normalize_path(str(route.path or ""))
        if not name or not method or not path:
            continue
        key = (method, path)
        version_meta = route_version_meta.get(name, {})
        version = _optional_text(version_meta.get("version"))
        entity_name = _optional_text(version_meta.get("entity_name")) or name
        status = _optional_text(version_meta.get("status")) or "active"
        replacement = _optional_text(version_meta.get("replacement"))
        deprecation_date = _optional_text(version_meta.get("deprecation_date"))
        seen_versions = seen_paths.setdefault(key, {})
        version_key = version or "__unversioned__"
        if version_key in seen_versions:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Route '{name}' duplicates {method} {path}.",
                    why="Each route version must be unique for the same method and path.",
                    fix="Use a unique version mapping in versions.yaml or change method/path.",
                    example='routes:\n  list_users:\n    - version: "1.0"\n      target: "list_users_v1"',
                ),
                line=route.line,
                column=route.column,
            )
        if version is None and seen_versions:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Route '{name}' conflicts with existing versioned routes.",
                    why=f"{method} {path} already has versioned entries.",
                    fix="Add route version metadata in versions.yaml for this route.",
                    example='routes:\n  list_users:\n    - version: "2.0"\n      target: "list_users"',
                ),
                line=route.line,
                column=route.column,
            )
        if version is not None and "__unversioned__" in seen_versions:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Route '{name}' conflicts with an unversioned route.",
                    why=f"{method} {path} is already owned by an unversioned entry.",
                    fix="Version all routes sharing this method/path.",
                    example='routes:\n  list_users:\n    - version: "1.0"\n      target: "list_users"',
                ),
                line=route.line,
                column=route.column,
            )
        seen_versions[version_key] = name
        segments, param_names = _compile_path(path)
        requirement = requirements.get(name)
        entries.append(
            RouteEntry(
                name=name,
                entity_name=entity_name,
                version=version,
                status=status,
                replacement=replacement,
                deprecation_date=deprecation_date,
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
    return sorted(
        entries,
        key=lambda entry: (
            entry.method,
            entry.path,
            entry.entity_name,
            entry.version or "",
            entry.name,
        ),
    )


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
        entry.entity_name,
        entry.version,
        entry.status,
        entry.replacement,
        entry.deprecation_date,
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


def _select_match(candidates: list[RouteMatch], *, requested_version: str | None) -> RouteMatch | None:
    if requested_version:
        exact = [item for item in candidates if (item.entry.version or "") == requested_version]
        exact_live = [item for item in exact if item.entry.status != "removed"]
        if exact_live:
            return sorted(exact_live, key=lambda item: _route_sort_key(item.entry))[-1]
        if exact:
            return None
    live = [item for item in candidates if item.entry.status != "removed"]
    if not live:
        return None
    return sorted(live, key=lambda item: _route_sort_key(item.entry))[-1]


def _route_sort_key(entry: RouteEntry) -> tuple:
    return (entry.entity_name, version_sort_key(entry.version), entry.name)


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text if text else None


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
