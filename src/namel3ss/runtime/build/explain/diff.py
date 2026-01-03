from __future__ import annotations

from typing import Any, Dict, List

from namel3ss.runtime.build.explain.manifest import BuildManifest


def _files_map(inputs: Dict[str, Any]) -> Dict[str, str]:
    files = inputs.get("files") if isinstance(inputs, dict) else None
    if not isinstance(files, list):
        return {}
    mapping: Dict[str, str] = {}
    for item in files:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        digest = item.get("sha256")
        if isinstance(path, str) and isinstance(digest, str):
            mapping[path] = digest
    return mapping


def diff_manifests(old: BuildManifest, new: BuildManifest) -> Dict[str, Any]:
    old_files = _files_map(old.inputs)
    new_files = _files_map(new.inputs)
    changed = sorted(
        path
        for path in set(old_files.keys()) | set(new_files.keys())
        if old_files.get(path) != new_files.get(path)
    )
    old_guarantees = set(old.guarantees)
    guarantees_added = [item for item in new.guarantees if item not in old_guarantees]
    return {
        "files_changed_count": len(changed),
        "files_changed": changed,
        "guarantees_added": guarantees_added,
    }


__all__ = ["diff_manifests"]
