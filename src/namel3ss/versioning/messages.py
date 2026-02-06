from __future__ import annotations

from pathlib import Path

from namel3ss.errors.guidance import build_guidance_message


def path_missing_message() -> str:
    return build_guidance_message(
        what="versions.yaml path could not be resolved.",
        why="Project root could not be derived from the app path.",
        fix="Run the command from a project with app.ai.",
        example="n3 version list",
    )


def invalid_file_message(path: Path, details: str) -> str:
    return build_guidance_message(
        what="versions.yaml is invalid.",
        why=f"{path.as_posix()} could not be parsed: {details}.",
        fix="Use routes, flows, and models mappings with version lists.",
        example='routes:\n  list_users:\n    - version: "1.0"\n      status: "active"',
    )


def invalid_section_message(path: Path, kind: str) -> str:
    return build_guidance_message(
        what=f"versions.yaml {kind} section is invalid.",
        why=f"Expected a mapping of entity names to version entries in {path.as_posix()}.",
        fix="Use a YAML mapping where each entity points to a list of version maps.",
        example='flows:\n  summarise:\n    - version: "2.0"\n      status: "active"',
    )


def invalid_entity_message(value: str) -> str:
    return build_guidance_message(
        what="Entity format is invalid.",
        why=f"Expected kind:name but got '{value}'.",
        fix="Use route:<name>, flow:<name>, or model:<name>.",
        example="n3 version add route:list_users 1.0",
    )


def invalid_kind_message(kind: str) -> str:
    return build_guidance_message(
        what=f"Version kind '{kind}' is invalid.",
        why="Only routes, flows, and models are supported.",
        fix="Use route, flow, or model.",
        example="n3 version list",
    )


def invalid_status_message(status: str) -> str:
    return build_guidance_message(
        what=f"Version status '{status}' is invalid.",
        why="Status must be active, deprecated, or removed.",
        fix="Use one of the allowed status values.",
        example='status: "deprecated"',
    )


def missing_value_message(label: str) -> str:
    return build_guidance_message(
        what=f"{label} is required.",
        why=f"A non-empty {label} value is required.",
        fix=f"Provide {label} and retry.",
        example="n3 version add flow:summarise 2.0",
    )


def duplicate_version_message(kind: str, entity: str, version: str) -> str:
    return build_guidance_message(
        what="Version already exists.",
        why=f"{kind}:{entity} already has version {version}.",
        fix="Choose a new version value or remove the existing one first.",
        example=f"n3 version remove {kind[:-1]}:{entity} {version}",
    )


def missing_entity_message(kind: str, entity: str) -> str:
    return build_guidance_message(
        what="Entity has no versions.",
        why=f"{kind}:{entity} is not in versions.yaml.",
        fix="Add a version entry first.",
        example=f"n3 version add {kind[:-1]}:{entity} 1.0",
    )


def missing_version_message(kind: str, entity: str, version: str) -> str:
    return build_guidance_message(
        what="Version not found.",
        why=f"{kind}:{entity} does not include version {version}.",
        fix="Use n3 version list to inspect available versions.",
        example="n3 version list --json",
    )


def remove_last_active_message(kind: str, entity: str, version: str) -> str:
    return build_guidance_message(
        what="Cannot remove the last active version.",
        why=f"{kind}:{entity} would have no active version after removing {version}.",
        fix="Add a replacement active version first.",
        example=f"n3 version add {kind[:-1]}:{entity} 2.0",
    )


__all__ = [
    "duplicate_version_message",
    "invalid_entity_message",
    "invalid_file_message",
    "invalid_kind_message",
    "invalid_section_message",
    "invalid_status_message",
    "missing_entity_message",
    "missing_value_message",
    "missing_version_message",
    "path_missing_message",
    "remove_last_active_message",
]
