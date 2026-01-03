from __future__ import annotations

from pathlib import Path

from namel3ss.runtime.build.explain.manifest import BuildManifest
from namel3ss.utils.json_tools import dumps


def write_history(project_root: Path, manifest: BuildManifest) -> Path:
    history_dir = project_root / ".namel3ss" / "build" / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    path = history_dir / f"{manifest.build_id}.json"
    payload = manifest.to_dict()
    path.write_text(dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


__all__ = ["write_history"]
