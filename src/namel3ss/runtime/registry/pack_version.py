from __future__ import annotations

from dataclasses import dataclass

from namel3ss.pkg.versions import Semver, parse_semver


@dataclass(frozen=True)
class PackVersion:
    raw: str
    kind: str
    semver: Semver | None


@dataclass(frozen=True)
class VersionComparison:
    status: str
    reason: str | None


def parse_pack_version(text: str) -> PackVersion:
    raw = str(text or "").strip()
    if raw == "stable":
        return PackVersion(raw=raw, kind="stable", semver=None)
    try:
        return PackVersion(raw=raw, kind="semver", semver=parse_semver(raw))
    except Exception:
        return PackVersion(raw=raw, kind="other", semver=None)


def version_sort_key(value: str | None) -> tuple[int, tuple[int, int, int], str]:
    if not isinstance(value, str):
        return (0, (0, 0, 0), "")
    parsed = parse_pack_version(value)
    if parsed.kind == "stable":
        return (2, (0, 0, 0), parsed.raw)
    if parsed.kind == "semver" and parsed.semver is not None:
        return (1, (parsed.semver.major, parsed.semver.minor, parsed.semver.patch), parsed.raw)
    return (0, (0, 0, 0), parsed.raw)


def compare_versions(installed: str | None, candidate: str | None) -> VersionComparison:
    if not installed or not candidate:
        return VersionComparison(status="unknown", reason="missing_version")
    if installed == candidate:
        return VersionComparison(status="same", reason=None)
    installed_info = parse_pack_version(installed)
    candidate_info = parse_pack_version(candidate)
    if installed_info.kind != "semver" or candidate_info.kind != "semver":
        return VersionComparison(status="unknown", reason="non_semver_version")
    if installed_info.semver is None or candidate_info.semver is None:
        return VersionComparison(status="unknown", reason="missing_semver")
    if installed_info.semver.major != candidate_info.semver.major:
        return VersionComparison(status="incompatible", reason="major_version_change")
    if candidate_info.semver > installed_info.semver:
        return VersionComparison(status="upgrade", reason=None)
    return VersionComparison(status="downgrade", reason=None)


__all__ = ["PackVersion", "VersionComparison", "compare_versions", "parse_pack_version", "version_sort_key"]
