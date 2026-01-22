from __future__ import annotations

from namel3ss.pkg.versions import parse_semver
from namel3ss.runtime.registry.pack_version.model import PackVersion


def parse_pack_version(text: str) -> PackVersion:
    raw = str(text or "").strip()
    if raw == "stable":
        return PackVersion(raw=raw, kind="stable", semver=None)
    try:
        return PackVersion(raw=raw, kind="semver", semver=parse_semver(raw))
    except Exception:
        return PackVersion(raw=raw, kind="other", semver=None)


__all__ = ["parse_pack_version"]
