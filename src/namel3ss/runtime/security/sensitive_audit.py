from __future__ import annotations

import json
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.persistence_paths import resolve_project_root


AUDIT_DIR = ".namel3ss/observability/audit"
AUDIT_FILE = "sensitive.jsonl"


def audit_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    root = resolve_project_root(project_root, app_path)
    if root is None:
        return None
    return root / AUDIT_DIR / AUDIT_FILE


def record_sensitive_access(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    flow_name: str,
    user: str,
    action: str,
    step_count: int,
    route_name: str | None = None,
) -> None:
    path = audit_path(project_root, app_path)
    if path is None:
        return
    entry = {
        "flow_name": flow_name,
        "user": user,
        "action": action,
        "step_count": int(step_count),
    }
    if route_name:
        entry["route"] = route_name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def read_sensitive_audit(project_root: str | Path | None, app_path: str | Path | None) -> list[dict]:
    path = audit_path(project_root, app_path)
    if path is None or not path.exists():
        return []
    entries: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            entries.append(parsed)
    return entries


def resolve_actor(identity: dict | None) -> str:
    if isinstance(identity, dict):
        for key in ("subject", "id", "email", "name"):
            value = identity.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return "anonymous"


def ensure_audit_available(project_root: str | Path | None, app_path: str | Path | None) -> Path:
    path = audit_path(project_root, app_path)
    if path is None:
        raise Namel3ssError(_missing_audit_path_message())
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _missing_audit_path_message() -> str:
    return build_guidance_message(
        what="Audit path could not be resolved.",
        why="The project root is missing.",
        fix="Run the command from a project folder or pass a valid app path.",
        example="n3 audit --json",
    )


__all__ = [
    "audit_path",
    "record_sensitive_access",
    "read_sensitive_audit",
    "resolve_actor",
    "ensure_audit_available",
]
