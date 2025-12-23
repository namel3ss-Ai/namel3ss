from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from namel3ss.errors.base import Namel3ssError
from namel3ss.pkg.checksums import verify_checksums
from namel3ss.pkg.lockfile import read_lockfile
from namel3ss.pkg.metadata import load_metadata
from namel3ss.pkg.types import Lockfile


@dataclass
class VerifyIssue:
    name: str
    message: str


def verify_installation(root: Path, lockfile: Lockfile | None = None) -> List[VerifyIssue]:
    issues: List[VerifyIssue] = []
    lock = lockfile or read_lockfile(root)
    packages_dir = root / "packages"
    if not packages_dir.exists():
        return [VerifyIssue(name="(packages)", message="packages/ directory is missing.")]
    for pkg in lock.packages:
        pkg_path = packages_dir / pkg.name
        if not pkg_path.exists():
            issues.append(VerifyIssue(name=pkg.name, message="Package directory is missing."))
            continue
        try:
            metadata = load_metadata(pkg_path)
        except Namel3ssError as err:
            issues.append(VerifyIssue(name=pkg.name, message=str(err)))
            continue
        if metadata.version != pkg.version:
            issues.append(
                VerifyIssue(
                    name=pkg.name,
                    message=f"Version mismatch: lockfile {pkg.version}, metadata {metadata.version}.",
                )
            )
        if metadata.source.as_string() != pkg.source.as_string():
            issues.append(
                VerifyIssue(
                    name=pkg.name,
                    message=f"Source mismatch: lockfile {pkg.source.as_string()}, metadata {metadata.source.as_string()}.",
                )
            )
        if pkg.license_id and metadata.license_id != pkg.license_id:
            issues.append(
                VerifyIssue(
                    name=pkg.name,
                    message=f"License mismatch: lockfile {pkg.license_id}, metadata {metadata.license_id}.",
                )
            )
        if pkg.license_file and metadata.license_file != pkg.license_file:
            issues.append(
                VerifyIssue(
                    name=pkg.name,
                    message=f"License file mismatch: lockfile {pkg.license_file}, metadata {metadata.license_file}.",
                )
            )
        try:
            actual = verify_checksums(pkg_path, pkg_path / metadata.checksums_file)
        except Namel3ssError as err:
            issues.append(VerifyIssue(name=pkg.name, message=str(err)))
            continue
        expected_map = {entry.path: entry.sha256 for entry in pkg.checksums}
        actual_map = {entry.path: entry.sha256 for entry in actual}
        if expected_map != actual_map:
            issues.append(
                VerifyIssue(
                    name=pkg.name,
                    message="Checksums do not match the lockfile.",
                )
            )
    return issues
