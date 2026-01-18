from __future__ import annotations

from pathlib import Path

from namel3ss.runtime.packs.broker import write_json


def run(payload):
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    path = payload.get("path")
    if not isinstance(path, str) or not path.strip():
        raise ValueError("payload.path must be a non-empty string")
    path = path.strip()
    if Path(path).is_absolute():
        raise ValueError("payload.path must be a relative path")
    data = payload.get("data")
    write_json(path, data, create_dirs=True)
    return {"ok": True, "path": path}
