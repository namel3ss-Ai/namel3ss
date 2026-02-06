from __future__ import annotations

import re


_SEMVER_RE = re.compile(
    r"^v?(?P<major>0|[1-9]\d*)"
    r"(?:\.(?P<minor>0|[1-9]\d*))?"
    r"(?:\.(?P<patch>0|[1-9]\d*))?"
    r"(?:-(?P<prerelease>[0-9A-Za-z.-]+))?"
    r"(?:\+[0-9A-Za-z.-]+)?$"
)


def version_sort_key(value: str | None) -> tuple:
    text = str(value or "").strip()
    parsed = _parse_semver(text)
    if parsed is None:
        return (0, -1, -1, -1, -1, (), text)
    major, minor, patch, prerelease = parsed
    # Stable releases sort higher than pre-releases with the same numeric core.
    prerelease_weight = 1 if prerelease is None else 0
    prerelease_key = _prerelease_sort_key(prerelease)
    return (1, major, minor, patch, prerelease_weight, prerelease_key, text)


def _parse_semver(value: str) -> tuple[int, int, int, str | None] | None:
    if not value:
        return None
    match = _SEMVER_RE.fullmatch(value)
    if match is None:
        return None
    major = int(match.group("major"))
    minor = int(match.group("minor") or "0")
    patch = int(match.group("patch") or "0")
    prerelease = match.group("prerelease")
    return (major, minor, patch, prerelease)


def _prerelease_sort_key(value: str | None) -> tuple[tuple[int, object], ...]:
    if not value:
        return ()
    parts: list[tuple[int, object]] = []
    for token in value.split("."):
        if token.isdigit():
            parts.append((0, int(token)))
        else:
            parts.append((1, token))
    return tuple(parts)


__all__ = ["version_sort_key"]
