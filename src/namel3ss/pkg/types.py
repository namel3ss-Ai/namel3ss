from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from namel3ss.pkg.versions import VersionConstraint


@dataclass(frozen=True)
class SourceSpec:
    scheme: str
    owner: str
    repo: str
    ref: str

    def as_string(self) -> str:
        return f"{self.scheme}:{self.owner}/{self.repo}@{self.ref}"


@dataclass
class DependencySpec:
    name: str
    source: SourceSpec
    constraint_raw: Optional[str] = None
    constraint: Optional[VersionConstraint] = None


@dataclass
class Manifest:
    dependencies: Dict[str, DependencySpec] = field(default_factory=dict)
    path: Optional[Path] = None


@dataclass(frozen=True)
class ChecksumEntry:
    path: str
    sha256: str


@dataclass
class PackageMetadata:
    name: str
    version: str
    source: SourceSpec
    license_id: Optional[str]
    license_file: Optional[str]
    checksums_file: str
    dependencies: List[DependencySpec] = field(default_factory=list)


@dataclass
class LockedPackage:
    name: str
    version: str
    source: SourceSpec
    license_id: Optional[str]
    license_file: Optional[str]
    checksums: List[ChecksumEntry] = field(default_factory=list)
    dependencies: List[DependencySpec] = field(default_factory=list)


@dataclass
class Lockfile:
    lockfile_version: int
    roots: List[DependencySpec] = field(default_factory=list)
    packages: List[LockedPackage] = field(default_factory=list)
