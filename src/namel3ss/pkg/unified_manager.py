from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.pkg.dependency_audit import load_audit_database, match_advisories
from namel3ss.pkg.graph import tree_lines
from namel3ss.pkg.index import get_entry, load_index
from namel3ss.pkg.install import FetchSession, install_from_resolution, lockfile_from_resolution
from namel3ss.pkg.lockfile import LOCKFILE_VERSION, LOCKFILE_FILENAME, UNIFIED_LOCKFILE_FILENAME, read_lockfile, write_lockfile
from namel3ss.pkg.manager import resolve_project
from namel3ss.pkg.manifest import load_manifest_optional, write_manifest
from namel3ss.pkg.plan import diff_lockfiles, plan_to_dict
from namel3ss.pkg.runtime_dependencies import (
    build_runtime_lock_entries,
    normalize_python_spec,
    normalize_system_spec,
    verify_runtime_lock_entry_with_artifacts,
)
from namel3ss.pkg.runtime_artifacts import (
    collect_python_artifact_checksums,
    collect_system_artifact_checksums,
)
from namel3ss.pkg.specs import parse_source_spec
from namel3ss.pkg.types import DependencySpec, Lockfile
from namel3ss.pkg.verify import verify_installation
from namel3ss.runtime.tools.python_env import app_venv_path, lockfile_path, venv_python_path

def dependency_add(root: Path, *, spec: str, dependency_type: str) -> dict[str, object]:
    manifest = load_manifest_optional(root)
    kind = str(dependency_type or "python").strip().lower()
    text = str(spec or "").strip()
    if not text:
        raise Namel3ssError(
            build_guidance_message(
                what="Dependency spec is missing.",
                why="Add commands require a dependency string.",
                fix="Pass a dependency value like requests@2.31.0.",
                example="n3 deps add requests@2.31.0",
            )
        )

    if kind == "python":
        normalized = normalize_python_spec(text)
        updated = sorted(set(manifest.runtime_python_dependencies + (normalized,)))
        manifest.runtime_python_dependencies = tuple(updated)
    elif kind == "system":
        normalized = normalize_system_spec(text)
        updated = sorted(set(manifest.runtime_system_dependencies + (normalized,)))
        manifest.runtime_system_dependencies = tuple(updated)
    else:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unsupported dependency type '{dependency_type}'.",
                why="Only python and system runtime dependency types are supported.",
                fix="Use --system for OS packages or omit it for python packages.",
                example="n3 deps add --system postgresql-client@13",
            )
        )

    write_manifest(root, manifest)
    return {
        "status": "ok",
        "dependency_type": kind,
        "added": normalized,
        "manifest_path": str((root / "namel3ss.toml").resolve()),
    }


def dependency_status(root: Path) -> dict[str, object]:
    manifest = load_manifest_optional(root)
    lockfile = _read_lockfile_optional(root)
    python_lock = lockfile_path(root)

    plan = []
    plan_error: str | None = None
    if manifest.dependencies:
        try:
            plan = _resolve_plan_changes(root, lockfile)
        except Namel3ssError as err:
            plan_error = str(err)

    payload: dict[str, object] = {
        "status": "ok",
        "manifest_path": str((root / "namel3ss.toml").resolve()),
        "lockfile_path": _lockfile_path_or_none(root),
        "python_lockfile_path": str(python_lock.resolve()) if python_lock.exists() else None,
        "packages_count": len(manifest.dependencies),
        "runtime_python_count": len(manifest.runtime_python_dependencies),
        "runtime_system_count": len(manifest.runtime_system_dependencies),
        "installed_package_count": len(lockfile.packages) if lockfile else 0,
        "installed_runtime_python_count": len(lockfile.python_packages) if lockfile else 0,
        "installed_runtime_system_count": len(lockfile.system_packages) if lockfile else 0,
        "plan": plan_to_dict(plan),
    }
    if plan_error:
        payload["plan_error"] = plan_error
    return payload


def dependency_install(
    root: Path,
    *,
    python_override: str | None = None,
    include_packages: bool = True,
    include_python: bool = True,
) -> dict[str, object]:
    manifest = load_manifest_optional(root)
    current = _read_lockfile_optional(root)

    lockfile = current or Lockfile(lockfile_version=LOCKFILE_VERSION, roots=[], packages=[])
    if include_packages:
        lockfile = _install_packages(root, manifest)

    freeze_lines: list[str] = []
    python_artifact_checksums: dict[str, str] = {}
    if include_python and manifest.runtime_python_dependencies:
        freeze_lines = _install_python_dependencies(
            root,
            manifest.runtime_python_dependencies,
            python_override=python_override,
        )
        python_artifact_checksums = collect_python_artifact_checksums(root)
    elif lockfile_path(root).exists():
        freeze_lines = _read_python_lock_lines(root)
        python_artifact_checksums = collect_python_artifact_checksums(root)

    system_artifact_checksums = collect_system_artifact_checksums(manifest.runtime_system_dependencies)
    python_entries, system_entries = build_runtime_lock_entries(
        manifest,
        freeze_lines=freeze_lines,
        python_artifact_checksums=python_artifact_checksums,
        system_artifact_checksums=system_artifact_checksums,
    )
    lockfile.python_packages = python_entries
    lockfile.system_packages = system_entries

    path = write_lockfile(root, lockfile)
    changes = diff_lockfiles(current, lockfile)
    return {
        "status": "ok",
        "lockfile": str(path.resolve()),
        "lockfile_alias": str((root / UNIFIED_LOCKFILE_FILENAME).resolve()),
        "python_lockfile": str(lockfile_path(root).resolve()) if lockfile_path(root).exists() else None,
        "changes": plan_to_dict(changes),
        "runtime_python": [entry.name for entry in python_entries],
        "runtime_system": [entry.name for entry in system_entries],
    }


def dependency_update(root: Path, *, python_override: str | None = None) -> dict[str, object]:
    manifest = load_manifest_optional(root)
    entries = load_index()

    updated: list[dict[str, str]] = []
    for name in sorted(manifest.dependencies.keys()):
        dep = manifest.dependencies[name]
        index_entry = get_entry(name, entries)
        if index_entry is None:
            continue
        recommended_source = parse_source_spec(index_entry.source_spec())
        if dep.source.scheme != recommended_source.scheme:
            continue
        if dep.source.owner != recommended_source.owner or dep.source.repo != recommended_source.repo:
            continue
        if dep.source.ref == recommended_source.ref:
            continue
        manifest.dependencies[name] = DependencySpec(
            name=name,
            source=recommended_source,
            constraint_raw=dep.constraint_raw,
            constraint=dep.constraint,
        )
        updated.append(
            {
                "name": name,
                "from": dep.source.as_string(),
                "to": recommended_source.as_string(),
            }
        )

    if updated:
        write_manifest(root, manifest)

    install_payload = dependency_install(root, python_override=python_override)
    install_payload["updated_packages"] = updated
    install_payload["updated_count"] = len(updated)
    return install_payload


def dependency_tree(root: Path) -> dict[str, object]:
    lockfile = read_lockfile(root)
    return {
        "status": "ok",
        "package_tree": tree_lines(lockfile),
        "runtime_python": [
            {
                "name": entry.name,
                "version": entry.version,
                "source": entry.source,
            }
            for entry in sorted(lockfile.python_packages, key=lambda item: item.name)
        ],
        "runtime_system": [
            {
                "name": entry.name,
                "version": entry.version,
                "source": entry.source,
            }
            for entry in sorted(lockfile.system_packages, key=lambda item: item.name)
        ],
    }


def dependency_verify(root: Path) -> dict[str, object]:
    lockfile = read_lockfile(root)
    package_issues = verify_installation(root, lockfile=lockfile)
    runtime_issues: list[dict[str, str]] = []
    python_artifact_checksums = collect_python_artifact_checksums(root)
    system_artifact_checksums = collect_system_artifact_checksums(
        tuple(entry.name for entry in lockfile.system_packages)
    )

    for entry in lockfile.python_packages + lockfile.system_packages:
        if verify_runtime_lock_entry_with_artifacts(
            entry,
            python_artifact_checksums=python_artifact_checksums,
            system_artifact_checksums=system_artifact_checksums,
        ):
            continue
        runtime_issues.append(
            {
                "name": entry.name,
                "message": (
                    "Runtime dependency checksum does not match lockfile entry "
                    "(or local artifact metadata is unavailable)."
                ),
            }
        )

    status = "ok" if not package_issues and not runtime_issues else "fail"
    return {
        "status": status,
        "package_issues": [
            {
                "name": issue.name,
                "message": issue.message,
            }
            for issue in package_issues
        ],
        "runtime_issues": runtime_issues,
    }


def dependency_audit(root: Path) -> dict[str, object]:
    lockfile = read_lockfile(root)
    advisories = load_audit_database()
    index_entries = {entry.name: entry for entry in load_index()}

    vulnerabilities: list[dict[str, object]] = []
    trust_warnings: list[dict[str, str]] = []

    for package in lockfile.packages:
        entry = index_entries.get(package.name)
        if entry is None:
            trust_warnings.append(
                {
                    "name": package.name,
                    "message": "Package is not in the official index; trust tier unknown.",
                }
            )
        elif entry.trust_tier == "community":
            trust_warnings.append(
                {
                    "name": package.name,
                    "message": "Package trust tier is community.",
                }
            )
        vulnerabilities.extend(match_advisories(advisories, name=package.name, version=package.version, source="pack"))

    for entry in lockfile.python_packages:
        vulnerabilities.extend(match_advisories(advisories, name=entry.name, version=entry.version, source="pypi"))

    for entry in lockfile.system_packages:
        vulnerabilities.extend(match_advisories(advisories, name=entry.name, version=entry.version, source="system"))

    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    vulnerabilities.sort(key=lambda row: (severity_order.get(str(row.get("severity", "low")).lower(), 9), str(row.get("name", ""))))

    return {
        "status": "ok" if not vulnerabilities else "fail",
        "vulnerabilities": vulnerabilities,
        "trust_warnings": trust_warnings,
        "summary": {
            "vulnerability_count": len(vulnerabilities),
            "trust_warning_count": len(trust_warnings),
        },
    }


def dependency_clean(root: Path, *, include_venv: bool = False) -> dict[str, object]:
    removed: list[str] = []
    for path in [
        root / "packages",
        root / LOCKFILE_FILENAME,
        root / UNIFIED_LOCKFILE_FILENAME,
        lockfile_path(root),
    ]:
        if not path.exists():
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        removed.append(str(path.resolve()))

    if include_venv:
        venv_path = app_venv_path(root)
        if venv_path.exists():
            shutil.rmtree(venv_path)
            removed.append(str(venv_path.resolve()))

    return {
        "status": "ok",
        "removed": removed,
    }


def _install_packages(root: Path, manifest) -> Lockfile:
    if not manifest.dependencies:
        current = _read_lockfile_optional(root)
        if current is not None:
            return current
        return Lockfile(lockfile_version=LOCKFILE_VERSION, roots=[], packages=[])

    session = FetchSession()
    try:
        manifest, resolution, session = resolve_project(root, session=session)
        return install_from_resolution(root, manifest.dependencies.values(), resolution, fetch_session=session)
    finally:
        session.close()


def _install_python_dependencies(
    root: Path,
    dependencies: tuple[str, ...],
    *,
    python_override: str | None,
) -> list[str]:
    specs: list[str] = []
    for spec in dependencies:
        normalized = normalize_python_spec(spec)
        if normalized:
            specs.append(normalized)
    if not specs:
        return []

    python_executable = Path(python_override) if python_override else Path(os.environ.get("PYTHON", sys.executable))
    if not python_executable.exists():
        raise Namel3ssError(
            build_guidance_message(
                what="Python interpreter not found.",
                why=f"Path '{python_executable}' does not exist.",
                fix="Provide a valid interpreter path with --python.",
                example="n3 install --python /usr/bin/python3",
            )
        )

    venv_path = app_venv_path(root)
    if not venv_path.exists():
        _run_subprocess(
            [str(python_executable), "-m", "venv", str(venv_path)],
            cwd=root,
            action="create venv",
        )
    venv_python = venv_python_path(venv_path)
    _run_subprocess(
        [str(venv_python), "-m", "pip", "install", *specs],
        cwd=root,
        action="install python runtime dependencies",
    )
    freeze_output = _run_subprocess(
        [str(venv_python), "-m", "pip", "freeze"],
        cwd=root,
        action="freeze python runtime dependencies",
        capture=True,
    )
    lines = [line for line in str(freeze_output or "").splitlines() if line.strip()]
    lines.sort()
    lockfile = lockfile_path(root)
    lockfile.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return lines


def _run_subprocess(
    cmd: list[str],
    *,
    cwd: Path,
    action: str,
    capture: bool = False,
) -> str | None:
    env = os.environ.copy()
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
    except FileNotFoundError as err:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Failed to {action}.",
                why=str(err),
                fix="Verify your environment and try again.",
                example="n3 install",
            )
        ) from err
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip() or "Subprocess exited with a non-zero status."
        raise Namel3ssError(
            build_guidance_message(
                what=f"Dependency operation failed while trying to {action}.",
                why=detail,
                fix="Check dependency declarations and retry.",
                example="n3 deps add requests@2.31.0",
            )
        )
    if capture:
        return result.stdout
    return None


def _read_lockfile_optional(root: Path) -> Lockfile | None:
    try:
        return read_lockfile(root)
    except Namel3ssError:
        return None


def _read_python_lock_lines(root: Path) -> list[str]:
    path = lockfile_path(root)
    if not path.exists():
        return []
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    lines.sort()
    return lines


def _resolve_plan_changes(root: Path, current: Lockfile | None):
    session = FetchSession()
    try:
        manifest, resolution, session = resolve_project(root, session=session)
        next_lock = lockfile_from_resolution(manifest.dependencies.values(), resolution, fetch_session=session)
    finally:
        session.close()
    return diff_lockfiles(current, next_lock)


def _lockfile_path_or_none(root: Path) -> str | None:
    unified = root / UNIFIED_LOCKFILE_FILENAME
    if unified.exists():
        return str(unified.resolve())
    legacy = root / LOCKFILE_FILENAME
    if legacy.exists():
        return str(legacy.resolve())
    return None


__all__ = [
    "dependency_add",
    "dependency_audit",
    "dependency_clean",
    "dependency_install",
    "dependency_status",
    "dependency_tree",
    "dependency_update",
    "dependency_verify",
]
