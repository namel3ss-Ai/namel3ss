from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.pkg.manifest import load_manifest_optional, write_manifest
from namel3ss.pkg.runtime_dependencies import normalize_python_spec, normalize_system_spec


def remove_runtime_dependency(root: Path, *, spec: str, dependency_type: str) -> dict[str, object]:
    manifest = load_manifest_optional(root)
    kind = str(dependency_type or "python").strip().lower()
    text = str(spec or "").strip()
    if not text:
        raise Namel3ssError(
            build_guidance_message(
                what="Dependency spec is missing.",
                why="remove requires a dependency identifier.",
                fix="Pass a dependency like requests==2.31.0.",
                example="n3 deps remove requests==2.31.0",
            )
        )

    if kind == "python":
        normalized = normalize_python_spec(text)
        current = list(manifest.runtime_python_dependencies)
        updated = [entry for entry in current if entry != normalized]
        removed = len(current) - len(updated)
        if removed == 0:
            return _not_found_payload(kind, normalized)
        manifest.runtime_python_dependencies = tuple(sorted(set(updated)))
    elif kind == "system":
        normalized = normalize_system_spec(text)
        current = list(manifest.runtime_system_dependencies)
        updated = [entry for entry in current if entry != normalized]
        removed = len(current) - len(updated)
        if removed == 0:
            return _not_found_payload(kind, normalized)
        manifest.runtime_system_dependencies = tuple(sorted(set(updated)))
    else:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unsupported dependency type '{dependency_type}'.",
                why="Only python and system runtime dependency types are supported.",
                fix="Use --system for OS packages or omit it for python packages.",
                example="n3 deps remove --system postgresql-client@13",
            )
        )

    write_manifest(root, manifest)
    return {
        "status": "ok",
        "dependency_type": kind,
        "removed": normalized,
        "manifest_path": str((root / "namel3ss.toml").resolve()),
    }


def _not_found_payload(kind: str, spec: str) -> dict[str, object]:
    return {
        "status": "fail",
        "dependency_type": kind,
        "removed": None,
        "reason": f"Dependency not found: {spec}",
    }


__all__ = ["remove_runtime_dependency"]
