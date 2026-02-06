from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.persistence_paths import resolve_project_root
from namel3ss.utils.simple_yaml import parse_yaml, render_yaml
from namel3ss.versioning.semver import version_sort_key
from namel3ss.versioning.messages import (
    duplicate_version_message,
    invalid_entity_message,
    invalid_file_message,
    invalid_kind_message,
    invalid_section_message,
    invalid_status_message,
    missing_entity_message,
    missing_value_message,
    missing_version_message,
    path_missing_message,
    remove_last_active_message,
)


VERSIONS_FILENAME = "versions.yaml"
ALLOWED_STATUSES = ("active", "deprecated", "removed")
KIND_MAP = {
    "route": "routes",
    "routes": "routes",
    "flow": "flows",
    "flows": "flows",
    "model": "models",
    "models": "models",
}


@dataclass(frozen=True)
class VersionEntry:
    version: str
    status: str
    target: str | None
    replacement: str | None
    deprecation_date: str | None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "version": self.version,
            "status": self.status,
        }
        if self.target:
            payload["target"] = self.target
        if self.replacement:
            payload["replacement"] = self.replacement
        if self.deprecation_date:
            payload["deprecation_date"] = self.deprecation_date
        return payload


@dataclass(frozen=True)
class VersionSpec:
    entity_name: str
    versions: tuple[VersionEntry, ...]

    def to_dict(self) -> list[dict[str, object]]:
        return [entry.to_dict() for entry in self.versions]


@dataclass(frozen=True)
class VersionConfig:
    routes: dict[str, VersionSpec]
    flows: dict[str, VersionSpec]
    models: dict[str, VersionSpec]

    def section(self, kind: str) -> dict[str, VersionSpec]:
        if kind == "routes":
            return self.routes
        if kind == "flows":
            return self.flows
        if kind == "models":
            return self.models
        raise Namel3ssError(invalid_kind_message(kind))

    def to_dict(self) -> dict[str, object]:
        return {
            "routes": {name: spec.to_dict() for name, spec in sorted(self.routes.items(), key=lambda item: item[0])},
            "flows": {name: spec.to_dict() for name, spec in sorted(self.flows.items(), key=lambda item: item[0])},
            "models": {name: spec.to_dict() for name, spec in sorted(self.models.items(), key=lambda item: item[0])},
        }


@dataclass(frozen=True)
class ResolvedVersion:
    kind: str
    entity_name: str
    entry: VersionEntry
    requested_version: str | None
    requested_removed: bool


def versions_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    root = resolve_project_root(project_root, app_path)
    if root is None:
        return None
    return Path(root) / VERSIONS_FILENAME


def load_version_config(project_root: str | Path | None, app_path: str | Path | None) -> VersionConfig:
    path = versions_path(project_root, app_path)
    if path is None or not path.exists():
        return VersionConfig(routes={}, flows={}, models={})
    try:
        payload = parse_yaml(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(invalid_file_message(path, str(err))) from err
    if not isinstance(payload, dict):
        raise Namel3ssError(invalid_file_message(path, "expected mapping"))
    return VersionConfig(
        routes=_parse_section(payload.get("routes"), path=path, kind="routes"),
        flows=_parse_section(payload.get("flows"), path=path, kind="flows"),
        models=_parse_section(payload.get("models"), path=path, kind="models"),
    )


def save_version_config(
    project_root: str | Path | None,
    app_path: str | Path | None,
    config: VersionConfig,
) -> Path:
    path = versions_path(project_root, app_path)
    if path is None:
        raise Namel3ssError(path_missing_message())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_yaml(config.to_dict()), encoding="utf-8")
    return path


def parse_entity_ref(raw: str) -> tuple[str, str]:
    token = str(raw or "").strip()
    if ":" not in token:
        raise Namel3ssError(invalid_entity_message(token))
    kind_raw, name_raw = token.split(":", 1)
    kind = KIND_MAP.get(kind_raw.strip().lower())
    name = name_raw.strip()
    if not kind or not name:
        raise Namel3ssError(invalid_entity_message(token))
    return kind, name


def list_versions(config: VersionConfig, *, kind: str | None = None) -> list[dict[str, object]]:
    kinds = [kind] if kind else ["routes", "flows", "models"]
    rows: list[dict[str, object]] = []
    for current in kinds:
        section = config.section(current)
        for entity_name in sorted(section.keys()):
            spec = section[entity_name]
            for entry in spec.versions:
                rows.append(
                    {
                        "kind": current,
                        "entity": entity_name,
                        "version": entry.version,
                        "status": entry.status,
                        "target": entry.target,
                        "replacement": entry.replacement,
                        "deprecation_date": entry.deprecation_date,
                    }
                )
    rows.sort(
        key=lambda row: (
            str(row["kind"]),
            str(row["entity"]),
            version_sort_key(str(row["version"])),
        )
    )
    return rows


def add_version(
    config: VersionConfig,
    *,
    kind: str,
    entity_name: str,
    version: str,
    target: str | None = None,
    status: str = "active",
    replacement: str | None = None,
    deprecation_date: str | None = None,
) -> VersionConfig:
    normalized_kind = _normalize_kind(kind)
    normalized_version = _normalize_version(version)
    normalized_status = _normalize_status(status)
    normalized_entity = _normalize_name(entity_name, "entity")
    normalized_target = _normalize_optional_name(target)
    normalized_replacement = _normalize_optional_name(replacement)
    normalized_eol = _normalize_optional_name(deprecation_date)

    section = _copy_section(config.section(normalized_kind))
    spec = section.get(normalized_entity, VersionSpec(entity_name=normalized_entity, versions=()))
    if any(item.version == normalized_version for item in spec.versions):
        raise Namel3ssError(duplicate_version_message(normalized_kind, normalized_entity, normalized_version))

    appended = list(spec.versions)
    appended.append(
        VersionEntry(
            version=normalized_version,
            status=normalized_status,
            target=normalized_target,
            replacement=normalized_replacement,
            deprecation_date=normalized_eol,
        )
    )
    section[normalized_entity] = VersionSpec(entity_name=normalized_entity, versions=_sort_versions(appended))
    return _replace_section(config, normalized_kind, section)


def deprecate_version(
    config: VersionConfig,
    *,
    kind: str,
    entity_name: str,
    version: str,
    replacement: str | None = None,
    deprecation_date: str | None = None,
) -> VersionConfig:
    normalized_kind = _normalize_kind(kind)
    normalized_entity = _normalize_name(entity_name, "entity")
    normalized_version = _normalize_version(version)
    normalized_replacement = _normalize_optional_name(replacement)
    normalized_eol = _normalize_optional_name(deprecation_date)

    section = _copy_section(config.section(normalized_kind))
    spec = section.get(normalized_entity)
    if spec is None:
        raise Namel3ssError(missing_entity_message(normalized_kind, normalized_entity))

    updated: list[VersionEntry] = []
    found = False
    for entry in spec.versions:
        if entry.version == normalized_version:
            updated.append(
                VersionEntry(
                    version=entry.version,
                    status="deprecated",
                    target=entry.target,
                    replacement=normalized_replacement or entry.replacement,
                    deprecation_date=normalized_eol or entry.deprecation_date,
                )
            )
            found = True
        else:
            updated.append(entry)
    if not found:
        raise Namel3ssError(missing_version_message(normalized_kind, normalized_entity, normalized_version))

    section[normalized_entity] = VersionSpec(entity_name=normalized_entity, versions=_sort_versions(updated))
    return _replace_section(config, normalized_kind, section)


def remove_version(
    config: VersionConfig,
    *,
    kind: str,
    entity_name: str,
    version: str,
    replacement: str | None = None,
) -> VersionConfig:
    normalized_kind = _normalize_kind(kind)
    normalized_entity = _normalize_name(entity_name, "entity")
    normalized_version = _normalize_version(version)
    normalized_replacement = _normalize_optional_name(replacement)

    section = _copy_section(config.section(normalized_kind))
    spec = section.get(normalized_entity)
    if spec is None:
        raise Namel3ssError(missing_entity_message(normalized_kind, normalized_entity))

    target = None
    kept: list[VersionEntry] = []
    for entry in spec.versions:
        if entry.version == normalized_version:
            target = entry
        else:
            kept.append(entry)
    if target is None:
        raise Namel3ssError(missing_version_message(normalized_kind, normalized_entity, normalized_version))

    active_count = len([entry for entry in spec.versions if entry.status == "active"])
    if target.status == "active" and active_count <= 1 and not normalized_replacement:
        raise Namel3ssError(remove_last_active_message(normalized_kind, normalized_entity, normalized_version))

    if not kept:
        section.pop(normalized_entity, None)
        return _replace_section(config, normalized_kind, section)

    if normalized_replacement:
        patched: list[VersionEntry] = []
        for entry in kept:
            if entry.version == normalized_replacement:
                patched.append(entry)
                continue
            patched.append(entry)
        kept = patched

    section[normalized_entity] = VersionSpec(entity_name=normalized_entity, versions=_sort_versions(kept))
    return _replace_section(config, normalized_kind, section)


def resolve_target_version(
    config: VersionConfig,
    *,
    kind: str,
    target_name: str,
    requested_version: str | None,
) -> ResolvedVersion | None:
    normalized_kind = _normalize_kind(kind)
    target = _normalize_name(target_name, "target")
    matches: list[tuple[str, VersionEntry]] = []
    for entity_name, spec in config.section(normalized_kind).items():
        for entry in spec.versions:
            entry_target = entry.target or entity_name
            if entry_target == target:
                matches.append((entity_name, entry))
    if not matches:
        return None

    if requested_version:
        normalized_requested = _normalize_version(requested_version)
        for entity_name, entry in matches:
            if entry.version == normalized_requested:
                return ResolvedVersion(
                    kind=normalized_kind,
                    entity_name=entity_name,
                    entry=entry,
                    requested_version=normalized_requested,
                    requested_removed=entry.status == "removed",
                )

    eligible = [(entity_name, entry) for entity_name, entry in matches if entry.status != "removed"]
    if not eligible:
        entity_name, entry = sorted(matches, key=lambda item: version_sort_key(item[1].version))[-1]
        return ResolvedVersion(
            kind=normalized_kind,
            entity_name=entity_name,
            entry=entry,
            requested_version=requested_version,
            requested_removed=entry.status == "removed",
        )

    entity_name, entry = sorted(eligible, key=lambda item: version_sort_key(item[1].version))[-1]
    return ResolvedVersion(
        kind=normalized_kind,
        entity_name=entity_name,
        entry=entry,
        requested_version=requested_version,
        requested_removed=False,
    )


def route_metadata_by_target(config: VersionConfig) -> dict[str, dict[str, object]]:
    metadata: dict[str, dict[str, object]] = {}
    for entity_name, spec in sorted(config.routes.items(), key=lambda item: item[0]):
        for entry in spec.versions:
            target = entry.target or entity_name
            metadata[target] = {
                "entity_name": entity_name,
                "version": entry.version,
                "status": entry.status,
                "replacement": entry.replacement,
                "deprecation_date": entry.deprecation_date,
            }
    return metadata


def _parse_section(payload: object, *, path: Path, kind: str) -> dict[str, VersionSpec]:
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise Namel3ssError(invalid_section_message(path, kind))
    result: dict[str, VersionSpec] = {}
    for raw_entity, raw_entries in payload.items():
        entity_name = _normalize_name(raw_entity, "entity")
        if not isinstance(raw_entries, list):
            raise Namel3ssError(invalid_section_message(path, kind))
        entries: list[VersionEntry] = []
        seen: set[str] = set()
        for item in raw_entries:
            if not isinstance(item, dict):
                raise Namel3ssError(invalid_section_message(path, kind))
            version = _normalize_version(item.get("version"))
            status = _normalize_status(item.get("status") or "active")
            target = _normalize_optional_name(item.get("target"))
            replacement = _normalize_optional_name(item.get("replacement"))
            deprecation_date = _normalize_optional_name(item.get("deprecation_date"))
            if version in seen:
                raise Namel3ssError(duplicate_version_message(kind, entity_name, version))
            seen.add(version)
            entries.append(
                VersionEntry(
                    version=version,
                    status=status,
                    target=target,
                    replacement=replacement,
                    deprecation_date=deprecation_date,
                )
            )
        result[entity_name] = VersionSpec(entity_name=entity_name, versions=_sort_versions(entries))
    return result


def _sort_versions(values: list[VersionEntry]) -> tuple[VersionEntry, ...]:
    return tuple(sorted(values, key=lambda item: version_sort_key(item.version)))


def _copy_section(section: dict[str, VersionSpec]) -> dict[str, VersionSpec]:
    copied: dict[str, VersionSpec] = {}
    for key, spec in section.items():
        copied[key] = VersionSpec(entity_name=spec.entity_name, versions=tuple(spec.versions))
    return copied


def _replace_section(config: VersionConfig, kind: str, section: dict[str, VersionSpec]) -> VersionConfig:
    if kind == "routes":
        return VersionConfig(routes=section, flows=config.flows, models=config.models)
    if kind == "flows":
        return VersionConfig(routes=config.routes, flows=section, models=config.models)
    if kind == "models":
        return VersionConfig(routes=config.routes, flows=config.flows, models=section)
    raise Namel3ssError(invalid_kind_message(kind))


def _normalize_kind(raw: object) -> str:
    token = str(raw or "").strip().lower()
    resolved = KIND_MAP.get(token)
    if resolved:
        return resolved
    raise Namel3ssError(invalid_kind_message(token))


def _normalize_name(raw: object, label: str) -> str:
    value = str(raw or "").strip()
    if value:
        return value
    raise Namel3ssError(missing_value_message(label))


def _normalize_optional_name(raw: object) -> str | None:
    if raw is None or isinstance(raw, bool):
        return None
    text = str(raw).strip()
    return text if text else None


def _normalize_version(raw: object) -> str:
    if isinstance(raw, bool) or raw is None:
        raise Namel3ssError(missing_value_message("version"))
    text = str(raw).strip()
    if text:
        return text
    raise Namel3ssError(missing_value_message("version"))


def _normalize_status(raw: object) -> str:
    text = str(raw or "").strip().lower()
    if text in ALLOWED_STATUSES:
        return text
    raise Namel3ssError(invalid_status_message(text))


__all__ = [
    "ALLOWED_STATUSES",
    "KIND_MAP",
    "ResolvedVersion",
    "VERSIONS_FILENAME",
    "VersionConfig",
    "VersionEntry",
    "VersionSpec",
    "add_version",
    "deprecate_version",
    "list_versions",
    "load_version_config",
    "parse_entity_ref",
    "remove_version",
    "resolve_target_version",
    "route_metadata_by_target",
    "save_version_config",
    "versions_path",
]
