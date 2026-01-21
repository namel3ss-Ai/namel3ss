from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable

from namel3ss.cli.builds import load_build_metadata, read_latest_build_id
from namel3ss.cli.targets_store import BUILD_BASE_DIR


def build_location(target: str, build_id: str) -> str:
    return f"{BUILD_BASE_DIR}/{target}/{build_id}"


def summarize_build_metadata(metadata: dict, *, target: str | None = None) -> Dict[str, Any]:
    resolved_target = target or metadata.get("target")
    build_id = metadata.get("build_id")
    summary: Dict[str, Any] = {
        "build_id": build_id,
        "target": resolved_target,
        "process_model": metadata.get("process_model"),
        "target_info": metadata.get("target_info", {}),
        "app_relative_path": metadata.get("app_relative_path"),
        "namel3ss_version": metadata.get("namel3ss_version"),
        "config_summary": metadata.get("config_summary", {}),
        "persistence_target": metadata.get("persistence_target"),
        "recommended_persistence": metadata.get("recommended_persistence"),
        "lockfile_status": metadata.get("lockfile_status"),
        "lockfile_digest": metadata.get("lockfile_digest"),
        "program_summary": metadata.get("program_summary", {}),
        "source_fingerprints": metadata.get("source_fingerprints", []),
        "artifacts": metadata.get("artifacts", {}),
        "entry_instructions": metadata.get("entry_instructions", {}),
    }
    if isinstance(build_id, str) and isinstance(resolved_target, str):
        summary["location"] = build_location(resolved_target, build_id)
    return summary


def load_build_summary(project_root: Path, target: str, build_id: str) -> Dict[str, Any]:
    _, metadata = load_build_metadata(project_root, target, build_id)
    return summarize_build_metadata(metadata, target=target)


def latest_build_ids(project_root: Path, targets: Iterable[str]) -> dict[str, str | None]:
    return {target: read_latest_build_id(project_root, target) for target in targets}


__all__ = ["build_location", "latest_build_ids", "load_build_summary", "summarize_build_metadata"]
