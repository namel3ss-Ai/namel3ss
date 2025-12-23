from __future__ import annotations

from dataclasses import dataclass
import re

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


SEMVER_RE = re.compile(r"^v?(?P<major>0|[1-9]\d*)(\.(?P<minor>0|[1-9]\d*))?(\.(?P<patch>0|[1-9]\d*))?$")


@dataclass(frozen=True, order=True)
class Semver:
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True)
class VersionConstraint:
    kind: str
    minimum: Semver
    maximum: Semver | None
    raw: str

    def matches(self, version: Semver) -> bool:
        if self.kind == "exact":
            return version == self.minimum
        if version < self.minimum:
            return False
        if self.maximum is not None and version >= self.maximum:
            return False
        return True


def parse_semver(text: str) -> Semver:
    match = SEMVER_RE.match(text.strip())
    if not match:
        raise Namel3ssError(
            build_guidance_message(
                what="Version is not valid semver.",
                why="Package versions must look like 0.1.2 (optionally prefixed with v).",
                fix="Use a semver version such as 0.1.2.",
                example="0.1.2",
            )
        )
    major = int(match.group("major"))
    minor = int(match.group("minor") or 0)
    patch = int(match.group("patch") or 0)
    return Semver(major=major, minor=minor, patch=patch)


def parse_constraint(text: str) -> VersionConstraint:
    raw = text.strip()
    if raw.startswith("="):
        version = parse_semver(raw[1:])
        return VersionConstraint(kind="exact", minimum=version, maximum=None, raw=raw)
    if raw.startswith("^"):
        version = parse_semver(raw[1:])
        maximum = _caret_max(version)
        return VersionConstraint(kind="caret", minimum=version, maximum=maximum, raw=raw)
    if raw.startswith("~"):
        version = parse_semver(raw[1:])
        maximum = Semver(version.major, version.minor + 1, 0)
        return VersionConstraint(kind="tilde", minimum=version, maximum=maximum, raw=raw)
    raise Namel3ssError(
        build_guidance_message(
            what="Version constraint is not supported.",
            why="Constraints must start with =, ^, or ~.",
            fix="Use =0.1.2, ^0.1, or ~0.1.2.",
            example="^0.1",
        )
    )


def _caret_max(version: Semver) -> Semver:
    if version.major > 0:
        return Semver(version.major + 1, 0, 0)
    if version.minor > 0:
        return Semver(version.major, version.minor + 1, 0)
    return Semver(version.major, version.minor, version.patch + 1)
