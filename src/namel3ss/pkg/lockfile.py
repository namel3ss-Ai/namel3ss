from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.pkg.specs import parse_source_spec
from namel3ss.pkg.types import ChecksumEntry, DependencySpec, Lockfile, LockedPackage, RuntimeLockEntry
from namel3ss.pkg.versions import parse_constraint
from namel3ss.utils.json_tools import dumps_pretty


LOCKFILE_FILENAME = "namel3ss.lock.json"
UNIFIED_LOCKFILE_FILENAME = "namel3ss.lock"
LOCKFILE_VERSION = 1


def read_lockfile(root: Path) -> Lockfile:
    path = _resolve_read_path(root)
    if path is None:
        raise Namel3ssError(
            build_guidance_message(
                what="Lockfile not found.",
                why=f"No {UNIFIED_LOCKFILE_FILENAME} or {LOCKFILE_FILENAME} exists in this project.",
                fix="Run `n3 install` or `n3 pkg install` to generate a lockfile.",
                example="n3 install",
            )
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Lockfile is not valid JSON.",
                why=f"JSON parsing failed: {err.msg}.",
                fix="Regenerate the lockfile with `n3 install`.",
                example="n3 install",
            )
        ) from err
    return _parse_lockfile_data(data)


def _resolve_read_path(root: Path) -> Path | None:
    unified_path = root / UNIFIED_LOCKFILE_FILENAME
    if unified_path.exists():
        return unified_path
    legacy_path = root / LOCKFILE_FILENAME
    if legacy_path.exists():
        return legacy_path
    return None


def write_lockfile(root: Path, lockfile: Lockfile) -> Path:
    payload = lockfile_to_dict(lockfile)
    rendered = dumps_pretty(payload)
    legacy_path = root / LOCKFILE_FILENAME
    unified_path = root / UNIFIED_LOCKFILE_FILENAME
    legacy_path.write_text(rendered, encoding="utf-8")
    unified_path.write_text(rendered, encoding="utf-8")
    return legacy_path


def lockfile_to_dict(lockfile: Lockfile) -> Dict[str, Any]:
    roots = [_dep_to_dict(dep) for dep in sorted(lockfile.roots, key=lambda d: d.name)]
    packages = [locked_package_to_dict(pkg) for pkg in sorted(lockfile.packages, key=lambda p: p.name)]
    payload: Dict[str, Any] = {
        "lockfile_version": lockfile.lockfile_version,
        "roots": roots,
        "packages": packages,
    }
    runtime_payload = _runtime_to_dict(lockfile)
    if runtime_payload:
        payload["runtime"] = runtime_payload
    return payload


def _runtime_to_dict(lockfile: Lockfile) -> Dict[str, Any]:
    python_entries = [runtime_lock_entry_to_dict(entry) for entry in sorted(lockfile.python_packages, key=lambda item: item.name)]
    system_entries = [runtime_lock_entry_to_dict(entry) for entry in sorted(lockfile.system_packages, key=lambda item: item.name)]
    if not python_entries and not system_entries:
        return {}
    payload: Dict[str, Any] = {}
    if python_entries:
        payload["python"] = python_entries
    if system_entries:
        payload["system"] = system_entries
    return payload


def runtime_lock_entry_to_dict(entry: RuntimeLockEntry) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "name": entry.name,
        "version": entry.version,
        "checksum": entry.checksum,
        "source": entry.source,
        "dependencies": dict(sorted(entry.dependencies.items())),
    }
    if entry.license:
        payload["license"] = entry.license
    if entry.trust_tier:
        payload["trust_tier"] = entry.trust_tier
    return payload


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
                fix="Regenerate the lockfile with `n3 install`.",
                example="n3 install",
            )
        )
    roots_raw = data.get("roots", [])
    packages_raw = data.get("packages", [])
    if not isinstance(roots_raw, list) or not isinstance(packages_raw, list):
        raise Namel3ssError(
            build_guidance_message(
                what="Lockfile structure is invalid.",
                why="Roots and packages must be arrays.",
                fix="Regenerate the lockfile with `n3 install`.",
                example="n3 install",
            )
        )
    roots = [_parse_dep_entry(entry, "root") for entry in roots_raw]
    packages = [_parse_package_entry(entry) for entry in packages_raw]

    runtime_raw = data.get("runtime")
    python_packages: list[RuntimeLockEntry] = []
    system_packages: list[RuntimeLockEntry] = []
    if runtime_raw is not None:
        if not isinstance(runtime_raw, dict):
            raise Namel3ssError(
                build_guidance_message(
                    what="Lockfile runtime section is invalid.",
                    why="runtime must be an object with python/system arrays.",
                    fix="Regenerate the lockfile with `n3 install`.",
                    example="n3 install",
                )
            )
        python_packages = _parse_runtime_entries(runtime_raw.get("python"), label="python")
        system_packages = _parse_runtime_entries(runtime_raw.get("system"), label="system")

    return Lockfile(
        lockfile_version=LOCKFILE_VERSION,
        roots=roots,
        packages=packages,
        python_packages=python_packages,
        system_packages=system_packages,
    )


def _parse_runtime_entries(value: object, *, label: str) -> list[RuntimeLockEntry]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise Namel3ssError(
            build_guidance_message(
                what=f"Lockfile runtime.{label} entry is invalid.",
                why=f"runtime.{label} must be an array of dependency objects.",
                fix="Regenerate the lockfile with `n3 install`.",
                example="n3 install",
            )
        )
    entries: list[RuntimeLockEntry] = []
    for item in value:
        if not isinstance(item, dict):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Lockfile runtime.{label} entry is invalid.",
                    why="Each runtime dependency must be an object.",
                    fix="Regenerate the lockfile with `n3 install`.",
                    example="n3 install",
                )
            )
        name = item.get("name")
        version = item.get("version")
        checksum = item.get("checksum")
        source = item.get("source")
        dependencies = item.get("dependencies", {})
        if not isinstance(name, str) or not isinstance(version, str) or not isinstance(checksum, str) or not isinstance(source, str):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Lockfile runtime.{label} entry is missing required fields.",
                    why="Each runtime dependency requires name, version, checksum, and source.",
                    fix="Regenerate the lockfile with `n3 install`.",
                    example="n3 install",
                )
            )
        if not isinstance(dependencies, dict):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Lockfile runtime.{label} dependency map is invalid.",
                    why="dependencies must be a map of dependency name to version.",
                    fix="Regenerate the lockfile with `n3 install`.",
                    example="n3 install",
                )
            )
        dep_map = {str(dep): str(dep_version) for dep, dep_version in sorted(dependencies.items(), key=lambda row: str(row[0]))}
        entries.append(
            RuntimeLockEntry(
                name=name,
                version=version,
                checksum=checksum,
                source=source,
                dependencies=dep_map,
                license=item.get("license") if isinstance(item.get("license"), str) else None,
                trust_tier=item.get("trust_tier") if isinstance(item.get("trust_tier"), str) else None,
            )
        )
    return sorted(entries, key=lambda entry: entry.name)


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


__all__ = [
    "LOCKFILE_FILENAME",
    "LOCKFILE_VERSION",
    "UNIFIED_LOCKFILE_FILENAME",
    "lockfile_to_dict",
    "read_lockfile",
    "runtime_lock_entry_to_dict",
    "write_lockfile",
]
