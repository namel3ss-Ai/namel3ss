from __future__ import annotations

import hashlib
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.pkg.checksums import verify_checksums
from namel3ss.pkg.lockfile import LOCKFILE_VERSION
from namel3ss.pkg.metadata import load_metadata
from namel3ss.pkg.resolver import ResolutionResult
from namel3ss.pkg.sources.github import GitHubFetcher
from namel3ss.pkg.types import ChecksumEntry, DependencySpec, Lockfile, LockedPackage, PackageMetadata, SourceSpec


PACKAGES_DIRNAME = "packages"


@dataclass
class PreparedPackage:
    root: Path
    metadata: PackageMetadata
    checksums: List[ChecksumEntry]


class FetchSession:
    def __init__(self, fetcher: GitHubFetcher | None = None) -> None:
        self._fetcher = fetcher or GitHubFetcher()
        self._tmpdir = tempfile.TemporaryDirectory()
        self._cache: Dict[str, Path] = {}

    def fetch(self, source: SourceSpec) -> Path:
        key = source.as_string()
        if key in self._cache:
            return self._cache[key]
        dest = Path(self._tmpdir.name) / _slugify(key)
        dest.mkdir(parents=True, exist_ok=True)
        root = self._fetcher.fetch(source, dest)
        self._cache[key] = root
        return root

    def close(self) -> None:
        self._tmpdir.cleanup()


def install_from_resolution(
    root: Path,
    roots: Iterable[DependencySpec],
    resolution: ResolutionResult,
    *,
    fetch_session: FetchSession | None = None,
) -> Lockfile:
    session = fetch_session or FetchSession()
    try:
        prepared = _prepare_packages(resolution, session)
        _install_packages(root, prepared)
        lockfile = _build_lockfile(roots, prepared)
        return lockfile
    finally:
        if fetch_session is None:
            session.close()


def lockfile_from_resolution(
    roots: Iterable[DependencySpec],
    resolution: ResolutionResult,
    *,
    fetch_session: FetchSession | None = None,
) -> Lockfile:
    session = fetch_session or FetchSession()
    try:
        prepared = _prepare_packages(resolution, session)
        return _build_lockfile(roots, prepared)
    finally:
        if fetch_session is None:
            session.close()


def _prepare_packages(resolution: ResolutionResult, session: FetchSession) -> Dict[str, PreparedPackage]:
    prepared: Dict[str, PreparedPackage] = {}
    for name in sorted(resolution.packages.keys()):
        expected = resolution.packages[name]
        root = session.fetch(expected.source)
        metadata = load_metadata(root)
        _validate_metadata(expected, metadata)
        checksums = verify_checksums(root, root / metadata.checksums_file)
        prepared[name] = PreparedPackage(root=root, metadata=metadata, checksums=checksums)
    return prepared


def _install_packages(root: Path, prepared: Dict[str, PreparedPackage]) -> None:
    packages_dir = root / PACKAGES_DIRNAME
    packages_dir.mkdir(parents=True, exist_ok=True)
    desired = set(prepared.keys())
    for name, pkg in prepared.items():
        target = packages_dir / name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(pkg.root, target)
    for existing in packages_dir.iterdir():
        if not existing.is_dir():
            continue
        if existing.name not in desired:
            shutil.rmtree(existing)


def _build_lockfile(roots: Iterable[DependencySpec], prepared: Dict[str, PreparedPackage]) -> Lockfile:
    packages: List[LockedPackage] = []
    for name in sorted(prepared.keys()):
        pkg = prepared[name]
        packages.append(
            LockedPackage(
                name=name,
                version=pkg.metadata.version,
                source=pkg.metadata.source,
                license_id=pkg.metadata.license_id,
                license_file=pkg.metadata.license_file,
                checksums=sorted(pkg.checksums, key=lambda c: c.path),
                dependencies=pkg.metadata.dependencies,
            )
        )
    return Lockfile(
        lockfile_version=LOCKFILE_VERSION,
        roots=sorted(list(roots), key=lambda d: d.name),
        packages=packages,
    )


def _validate_metadata(expected: PackageMetadata, actual: PackageMetadata) -> None:
    if actual.name != expected.name:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Package name mismatch for '{expected.name}'.",
                why=f"Downloaded package declares name '{actual.name}'.",
                fix="Check the package metadata or dependency name.",
                example=f'{expected.name} = "{expected.source.as_string()}"',
            )
        )
    if actual.source.as_string() != expected.source.as_string():
        raise Namel3ssError(
            build_guidance_message(
                what=f"Package source mismatch for '{expected.name}'.",
                why=f"Metadata declares {actual.source.as_string()}, expected {expected.source.as_string()}.",
                fix="Use the correct source or update the package metadata.",
                example=expected.source.as_string(),
            )
        )


def _slugify(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return digest[:12]
