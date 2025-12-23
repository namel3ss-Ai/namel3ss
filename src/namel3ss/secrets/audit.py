from __future__ import annotations

import json
import os
import time
from pathlib import Path

from namel3ss.secrets.context import get_audit_root, get_engine_target
from namel3ss.utils.json_tools import dumps as json_dumps


AUDIT_FILENAME = ".namel3ss/secret_audit.jsonl"
ENV_AUDIT_PATH = "N3_SECRET_AUDIT_PATH"


def secret_audit_path(project_root: Path | None) -> Path | None:
    override = os.getenv(ENV_AUDIT_PATH, "").strip()
    if override:
        return _normalize_override_path(override)
    if project_root is None:
        return None
    return project_root / AUDIT_FILENAME


def record_secret_access(
    name: str,
    *,
    caller: str,
    target: str | None = None,
    source: str | None = None,
    project_root: Path | None = None,
) -> None:
    root = project_root or get_audit_root()
    path = secret_audit_path(root)
    if path is None:
        return
    payload = {
        "secret_name": name,
        "time": time.time(),
        "caller": caller,
        "target": target or get_engine_target(),
        "source": source or "env",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json_dumps(payload) + "\n")


def read_secret_audit(project_root: Path) -> list[dict]:
    path = secret_audit_path(project_root)
    if path is None or not path.exists():
        return []
    events: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def _normalize_override_path(raw: str) -> Path:
    path = Path(raw).expanduser()
    if path.suffix == ".jsonl":
        return path
    return path / "secret_audit.jsonl"


__all__ = ["AUDIT_FILENAME", "ENV_AUDIT_PATH", "secret_audit_path", "record_secret_access", "read_secret_audit"]
