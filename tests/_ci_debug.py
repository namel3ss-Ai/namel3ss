from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path


_ENV_EXACT = {"N3_EXECUTABLE_SPEC", "UPDATE_SNAPSHOTS"}
_ENV_KEYWORDS = ("TOOL", "BIND")


def debug_context(tag: str, *, app_root: Path | None = None) -> dict[str, object]:
    env = _select_env()
    tools_yaml = _read_tools_yaml(app_root)
    return {
        "tag": tag,
        "cwd": str(Path.cwd()),
        "python_executable": sys.executable,
        "python_version": sys.version,
        "os_name": os.name,
        "platform": platform.platform(),
        "env": env,
        "node_path": shutil.which("node"),
        "tools_yaml": tools_yaml,
    }


def _select_env() -> dict[str, str | None]:
    selected: dict[str, str | None] = {}
    for key in sorted(os.environ):
        if key in _ENV_EXACT:
            selected[key] = os.environ.get(key)
            continue
        if not key.startswith("N3_"):
            continue
        if any(token in key for token in _ENV_KEYWORDS):
            selected[key] = os.environ.get(key)
    for key in sorted(_ENV_EXACT):
        selected.setdefault(key, os.environ.get(key))
    return selected


def _read_tools_yaml(app_root: Path | None) -> dict[str, object]:
    if app_root is None:
        return {"path": None, "exists": False}
    path = app_root / ".namel3ss" / "tools.yaml"
    if not path.exists():
        return {"path": str(path), "exists": False}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()[:30]
    except Exception as err:  # pragma: no cover - diagnostic only
        return {"path": str(path), "exists": True, "error": str(err)}
    return {"path": str(path), "exists": True, "head": lines}


__all__ = ["debug_context"]
