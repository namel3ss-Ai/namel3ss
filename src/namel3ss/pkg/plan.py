from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from namel3ss.pkg.types import Lockfile


@dataclass
class PlanChange:
    kind: str
    name: str
    from_version: str | None = None
    to_version: str | None = None


def diff_lockfiles(current: Lockfile | None, next_lock: Lockfile) -> List[PlanChange]:
    current_map = _package_versions(current)
    next_map = _package_versions(next_lock)
    changes: List[PlanChange] = []

    for name in sorted(next_map.keys() - current_map.keys()):
        changes.append(PlanChange(kind="add", name=name, to_version=next_map[name]))
    for name in sorted(current_map.keys() - next_map.keys()):
        changes.append(PlanChange(kind="remove", name=name, from_version=current_map[name]))
    for name in sorted(current_map.keys() & next_map.keys()):
        if current_map[name] != next_map[name]:
            changes.append(
                PlanChange(kind="update", name=name, from_version=current_map[name], to_version=next_map[name])
            )
    return changes


def plan_to_dict(changes: List[PlanChange]) -> dict:
    return {
        "changes": [
            {
                "kind": c.kind,
                "name": c.name,
                **({"from_version": c.from_version} if c.from_version else {}),
                **({"to_version": c.to_version} if c.to_version else {}),
            }
            for c in changes
        ]
    }


def _package_versions(lockfile: Lockfile | None) -> Dict[str, str]:
    if lockfile is None:
        return {}
    return {pkg.name: pkg.version for pkg in lockfile.packages}
