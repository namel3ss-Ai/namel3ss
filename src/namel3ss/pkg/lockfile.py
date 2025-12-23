from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.pkg.specs import parse_source_spec
from namel3ss.pkg.types import ChecksumEntry, DependencySpec, Lockfile, LockedPackage
from namel3ss.pkg.versions import parse_constraint
from namel3ss.utils.json_tools import dumps_pretty


LOCKFILE_FILENAME = "namel3ss.lock.json"
LOCKFILE_VERSION = 1


def read_lockfile(root: Path) -> Lockfile:
    path = root / LOCKFILE_FILENAME
    if not path.exists():
        raise Namel3ssError(
            build_guidance_message(
                what="Lockfile not found.",
                why="No namel3ss.lock.json exists in this project.",
                fix="Run `n3 pkg install` to generate a lockfile.",
                example="n3 pkg install",
            )
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Lockfile is not valid JSON.",
                why=f"JSON parsing failed: {err.msg}.",
                fix="Regenerate the lockfile with `n3 pkg install`.",
                example="n3 pkg install",
            )
        ) from err
    return _parse_lockfile_data(data)


def write_lockfile(root: Path, lockfile: Lockfile) -> Path:
    path = root / LOCKFILE_FILENAME
    payload = lockfile_to_dict(lockfile)
    path.write_text(dumps_pretty(payload), encoding="utf-8")
    return path


def lockfile_to_dict(lockfile: Lockfile) -> Dict[str, Any]:
    roots = [_dep_to_dict(dep) for dep in sorted(lockfile.roots, key=lambda d: d.name)]
    packages = [locked_package_to_dict(pkg) for pkg in sorted(lockfile.packages, key=lambda p: p.name)]
    return {
        "lockfile_version": lockfile.lockfile_version,
        "roots": roots,
        "packages": packages,
    }


def locked_package_to_dict(pkg: LockedPackage) -> Dict[str, Any]:
    deps = [_dep_to_dict(dep) for dep in sorted(pkg.dependencies, key=lambda d: d.name)]
    checksums = [entry.__dict__ for entry in sorted(pkg.checksums, key=lambda c: c.path)]
    data: Dict[str, Any] = {
        "name": pkg.name,
        "version": pkg.version,
        "source": pkg.source.as_string(),
        "checksums": checksums,
        "dependencies": deps,
    }
    if pkg.license_id:
        data["license"] = pkg.license_id
    if pkg.license_file:
        data["license_file"] = pkg.license_file
    return data


def _parse_lockfile_data(data: Dict[str, Any]) -> Lockfile:
    version = data.get("lockfile_version")
    if version != LOCKFILE_VERSION:
        raise Namel3ssError(
            build_guidance_message(
                what="Lockfile version is unsupported.",
                why=f"Expected lockfile_version {LOCKFILE_VERSION}.",
                fix="Regenerate the lockfile with `n3 pkg install`.",
                example="n3 pkg install",
            )
        )
    roots_raw = data.get("roots", [])
    packages_raw = data.get("packages", [])
    if not isinstance(roots_raw, list) or not isinstance(packages_raw, list):
        raise Namel3ssError(
            build_guidance_message(
                what="Lockfile structure is invalid.",
                why="Roots and packages must be arrays.",
                fix="Regenerate the lockfile with `n3 pkg install`.",
                example="n3 pkg install",
            )
        )
    roots = [_parse_dep_entry(entry, "root") for entry in roots_raw]
    packages = [_parse_package_entry(entry) for entry in packages_raw]
    return Lockfile(lockfile_version=LOCKFILE_VERSION, roots=roots, packages=packages)


def _parse_dep_entry(entry: Dict[str, Any], label: str) -> DependencySpec:
    if not isinstance(entry, dict):
        raise Namel3ssError(
            build_guidance_message(
                what=f"Lockfile {label} entry is invalid.",
                why="Each entry must be an object.",
                fix="Regenerate the lockfile with `n3 pkg install`.",
                example="n3 pkg install",
            )
        )
    name = entry.get("name")
    source_value = entry.get("source")
    constraint_value = entry.get("version")
    if not isinstance(name, str) or not isinstance(source_value, str):
        raise Namel3ssError(
            build_guidance_message(
                what=f"Lockfile {label} entry is missing required fields.",
                why="Each entry requires name and source.",
                fix="Regenerate the lockfile with `n3 pkg install`.",
                example="n3 pkg install",
            )
        )
    source = parse_source_spec(source_value)
    constraint = None
    if isinstance(constraint_value, str):
        constraint = parse_constraint(constraint_value)
    return DependencySpec(name=name, source=source, constraint_raw=constraint_value, constraint=constraint)


def _parse_package_entry(entry: Dict[str, Any]) -> LockedPackage:
    if not isinstance(entry, dict):
        raise Namel3ssError(
            build_guidance_message(
                what="Lockfile package entry is invalid.",
                why="Each package entry must be an object.",
                fix="Regenerate the lockfile with `n3 pkg install`.",
                example="n3 pkg install",
            )
        )
    name = entry.get("name")
    version = entry.get("version")
    source_value = entry.get("source")
    if not isinstance(name, str) or not isinstance(version, str) or not isinstance(source_value, str):
        raise Namel3ssError(
            build_guidance_message(
                what="Lockfile package entry is missing required fields.",
                why="Packages require name, version, and source.",
                fix="Regenerate the lockfile with `n3 pkg install`.",
                example="n3 pkg install",
            )
        )
    source = parse_source_spec(source_value)
    checksums_raw = entry.get("checksums", [])
    if not isinstance(checksums_raw, list):
        raise Namel3ssError(
            build_guidance_message(
                what=f"Lockfile package '{name}' checksums are invalid.",
                why="Checksums must be an array of {path, sha256}.",
                fix="Regenerate the lockfile with `n3 pkg install`.",
                example="n3 pkg install",
            )
        )
    checksums = []
    for item in checksums_raw:
        if not isinstance(item, dict) or "path" not in item or "sha256" not in item:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Lockfile package '{name}' checksum entry is invalid.",
                    why="Each checksum must include path and sha256.",
                    fix="Regenerate the lockfile with `n3 pkg install`.",
                    example="n3 pkg install",
                )
            )
        checksums.append(ChecksumEntry(path=item["path"], sha256=item["sha256"]))
    deps_raw = entry.get("dependencies", [])
    if not isinstance(deps_raw, list):
        raise Namel3ssError(
            build_guidance_message(
                what=f"Lockfile package '{name}' dependencies are invalid.",
                why="Dependencies must be an array.",
                fix="Regenerate the lockfile with `n3 pkg install`.",
                example="n3 pkg install",
            )
        )
    deps = [_parse_dep_entry(dep, "dependency") for dep in deps_raw]
    license_id = entry.get("license") if isinstance(entry.get("license"), str) else None
    license_file = entry.get("license_file") if isinstance(entry.get("license_file"), str) else None
    return LockedPackage(
        name=name,
        version=version,
        source=source,
        license_id=license_id,
        license_file=license_file,
        checksums=checksums,
        dependencies=deps,
    )


def _dep_to_dict(dep: DependencySpec) -> Dict[str, Any]:
    data: Dict[str, Any] = {"name": dep.name, "source": dep.source.as_string()}
    if dep.constraint_raw:
        data["version"] = dep.constraint_raw
    return data
