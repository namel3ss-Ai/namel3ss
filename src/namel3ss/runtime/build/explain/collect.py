from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def collect_inputs(project_root: Path, app_path: Path) -> Dict[str, Any]:
    text = app_path.read_text(encoding="utf-8")
    fingerprint = _hash_text(text)
    try:
        rel = app_path.resolve().relative_to(project_root.resolve())
    except ValueError:
        rel = Path(app_path.name)
    files = [{"path": rel.as_posix(), "sha256": fingerprint}]
    return {"source_fingerprint": fingerprint, "files": files, "config": {}}


__all__ = ["collect_inputs"]
