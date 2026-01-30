from __future__ import annotations

import json
from pathlib import Path

from namel3ss.determinism import canonical_json_dumps
from namel3ss.runtime.persistence_paths import resolve_persistence_root


CACHE_DIR = "cache"
QUARANTINE_DIR = "quarantine"


def gate_root(project_root: str | None, app_path: str | None) -> Path | None:
    root = resolve_persistence_root(project_root, app_path, allow_create=True)
    if root is None:
        return None
    return root / ".namel3ss" / "ingestion"


def cache_entry_path(root: Path, key: str) -> Path:
    return root / CACHE_DIR / f"{key}.json"


def quarantine_entry_path(root: Path, key: str) -> Path:
    return root / QUARANTINE_DIR / f"{key}.json"


def read_cache_entry(root: Path | None, key: str) -> dict | None:
    if root is None:
        return None
    path = cache_entry_path(root, key)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def write_cache_entry(root: Path | None, key: str, entry: dict) -> None:
    if root is None:
        return
    path = cache_entry_path(root, key)
    _write_json(path, entry)


def write_quarantine_entry(root: Path | None, key: str, entry: dict) -> None:
    if root is None:
        return
    path = quarantine_entry_path(root, key)
    _write_json(path, entry)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = canonical_json_dumps(payload, pretty=True, drop_run_keys=False)
    path.write_text(text, encoding="utf-8")


__all__ = [
    "cache_entry_path",
    "gate_root",
    "quarantine_entry_path",
    "read_cache_entry",
    "write_cache_entry",
    "write_quarantine_entry",
]
