from __future__ import annotations

import json
from pathlib import Path

from namel3ss_safeio import safe_open


def read_text(payload: dict) -> dict:
    path = _safe_path(payload)
    encoding = _read_encoding(payload)
    with safe_open(path, "r", encoding=encoding) as handle:
        return {"text": handle.read()}


def write_text(payload: dict) -> dict:
    path = _safe_path(payload)
    text = payload.get("text")
    if not isinstance(text, str):
        raise ValueError("payload.text must be a string")
    encoding = _read_encoding(payload)
    create_dirs = bool(payload.get("create_dirs", False))
    with safe_open(path, "w", encoding=encoding, create_dirs=create_dirs) as handle:
        handle.write(text)
    return {"ok": True, "path": str(path)}


def read_json(payload: dict) -> dict:
    path = _safe_path(payload)
    encoding = _read_encoding(payload)
    with safe_open(path, "r", encoding=encoding) as handle:
        raw = handle.read()
    return {"data": json.loads(raw)}


def write_json(payload: dict) -> dict:
    path = _safe_path(payload)
    data = payload.get("data", {})
    encoding = _read_encoding(payload)
    create_dirs = bool(payload.get("create_dirs", False))
    with safe_open(path, "w", encoding=encoding, create_dirs=create_dirs) as handle:
        handle.write(json.dumps(data, indent=2, sort_keys=True))
    return {"ok": True, "path": str(path)}


def _safe_path(payload: dict) -> Path:
    value = payload.get("path")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("payload.path must be a non-empty string")
    raw = value.strip()
    candidate = Path(raw)
    if candidate.is_absolute():
        raise ValueError("payload.path must be a relative path")
    base = Path.cwd().resolve()
    resolved = (base / candidate).resolve()
    if not resolved.is_relative_to(base):
        raise ValueError("payload.path must stay within the app directory")
    return resolved


def _read_encoding(payload: dict) -> str:
    encoding = payload.get("encoding", "utf-8")
    if not isinstance(encoding, str) or not encoding.strip():
        raise ValueError("payload.encoding must be a string")
    return encoding.strip()


__all__ = ["read_json", "read_text", "write_json", "write_text"]
