from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.pkg.specs import parse_source_spec
from namel3ss.pkg.types import DependencySpec, PackageMetadata
from namel3ss.pkg.versions import parse_constraint


METADATA_FILENAME = "namel3ss.package.json"


def load_metadata(package_root: Path) -> PackageMetadata:
    metadata_path = package_root / METADATA_FILENAME
    if not metadata_path.exists():
        raise Namel3ssError(
            build_guidance_message(
                what="Package metadata file is missing.",
                why=f"Expected {METADATA_FILENAME} in the package root.",
                fix=f"Add {METADATA_FILENAME} to the package.",
                example=METADATA_FILENAME,
            )
        )
    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Package metadata is not valid JSON.",
                why=f"JSON parsing failed: {err.msg}.",
                fix="Fix the JSON in the package metadata.",
                example='{"name":"inventory","version":"0.1.0"}',
            )
        ) from err

    name = data.get("name")
    version = data.get("version")
    source_value = data.get("source")
    checksums_file = data.get("checksums")
    if not isinstance(name, str) or not isinstance(version, str) or not isinstance(source_value, str):
        raise Namel3ssError(
            build_guidance_message(
                what="Package metadata is missing required fields.",
                why="name, version, and source are required.",
                fix="Add the required fields to the metadata file.",
                example='{"name":"inventory","version":"0.1.0","source":"github:owner/repo@v0.1.0"}',
            )
        )
    if not isinstance(checksums_file, str):
        raise Namel3ssError(
            build_guidance_message(
                what="Package checksums manifest is missing.",
                why="Each package must declare a checksums file.",
                fix='Add "checksums": "checksums.json" to the metadata.',
                example='"checksums": "checksums.json"',
            )
        )
    source = parse_source_spec(source_value)
    license_id = data.get("license") if isinstance(data.get("license"), str) else None
    license_file = data.get("license_file") if isinstance(data.get("license_file"), str) else None
    if not license_id and not license_file:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Package '{name}' does not declare a license.",
                why="Packages must include a license id or license file.",
                fix="Add a SPDX license id or a license_file entry.",
                example='"license": "MIT"',
            )
        )
    if license_file:
        license_path = package_root / license_file
        if not license_path.exists():
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Package '{name}' license file was not found.",
                    why=f"Expected {license_file} at {license_path.as_posix()}.",
                    fix="Add the license file or update the license_file path.",
                    example="LICENSE",
                )
            )
    capsule_path = package_root / "capsule.ai"
    if not capsule_path.exists():
        raise Namel3ssError(
            build_guidance_message(
                what=f"Package '{name}' is missing capsule.ai.",
                why="Every package must include capsule.ai in its root.",
                fix="Add capsule.ai to the package.",
                example="capsule.ai",
            )
        )
    dependencies = _parse_dependencies(data.get("dependencies"))
    return PackageMetadata(
        name=name,
        version=version,
        source=source,
        license_id=license_id,
        license_file=license_file,
        checksums_file=checksums_file,
        dependencies=dependencies,
    )


def _parse_dependencies(value: Any) -> list[DependencySpec]:
    if value is None:
        return []
    if not isinstance(value, dict):
        raise Namel3ssError(
            build_guidance_message(
                what="Package dependencies are invalid.",
                why="Dependencies must be a mapping of name to source.",
                fix="Use a mapping like {\"shared\": {\"source\": \"github:owner/repo@v0.1.0\"}}.",
                example='"dependencies": {"shared": {"source": "github:owner/repo@v0.1.0"}}',
            )
        )
    deps: list[DependencySpec] = []
    for name, entry in value.items():
        deps.append(_parse_dependency(name, entry))
    return deps


def _parse_dependency(name: str, entry: Any) -> DependencySpec:
    if isinstance(entry, str):
        source = parse_source_spec(entry)
        return DependencySpec(name=name, source=source)
    if isinstance(entry, dict):
        source_value = entry.get("source")
        version_value = entry.get("version")
        if not isinstance(source_value, str):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Dependency '{name}' is missing a source.",
                    why="Each dependency must include a GitHub source.",
                    fix="Add a source field to the dependency.",
                    example=f'"{name}": {{"source": "github:owner/repo@v0.1.0"}}',
                )
            )
        source = parse_source_spec(source_value)
        constraint = None
        if version_value is not None:
            if not isinstance(version_value, str):
                raise Namel3ssError(
                    build_guidance_message(
                        what=f"Dependency '{name}' has an invalid version constraint.",
                        why="Version constraints must be strings like ^0.1 or =0.1.2.",
                        fix="Use a valid version constraint string.",
                        example=f'"{name}": {{"source": "github:owner/repo@v0.1.0", "version": "^0.1"}}',
                    )
                )
            constraint = parse_constraint(version_value)
        return DependencySpec(name=name, source=source, constraint_raw=version_value, constraint=constraint)
    raise Namel3ssError(
        build_guidance_message(
            what=f"Dependency '{name}' has an unsupported value.",
            why="Dependencies must be strings or objects with source/version.",
            fix="Use a GitHub source string or an object with source/version.",
            example=f'"{name}": {{"source": "github:owner/repo@v0.1.0"}}',
        )
    )
