from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


PATTERN_SCHEMA_VERSION = 1
PATTERN_PATH_ENV = "N3_PATTERNS_PATH"
DEFAULT_INDEX_PATH = Path(__file__).resolve().parents[3] / "patterns" / "index.json"


@dataclass(frozen=True)
class PatternEntry:
    id: str
    description: str
    path: Path

    def to_dict(self) -> dict:
        return {"id": self.id, "description": self.description, "path": self.path.as_posix()}


def load_patterns(index_path: Path | None = None) -> list[PatternEntry]:
    path = _resolve_index_path(index_path)
    data = _read_index(path)
    errors = _validate_index(data)
    if errors:
        raise Namel3ssError(
            build_guidance_message(
                what="Patterns index is invalid.",
                why="; ".join(errors),
                fix="Fix the patterns/index.json schema.",
                example="patterns/index.json",
            )
        )
    base_dir = path.parent
    patterns: list[PatternEntry] = []
    for entry in data.get("patterns", []):
        entry_id = str(entry.get("id"))
        description = str(entry.get("description"))
        rel_path = entry.get("path") or entry_id
        pattern_path = (base_dir / str(rel_path)).resolve()
        patterns.append(PatternEntry(id=entry_id, description=description, path=pattern_path))
    return sorted(patterns, key=lambda item: item.id)


def get_pattern(pattern_id: str, patterns: list[PatternEntry]) -> PatternEntry | None:
    needle = pattern_id.strip().lower()
    for pattern in patterns:
        if pattern.id.lower() == needle:
            return pattern
    return None


def _resolve_index_path(index_path: Path | None) -> Path:
    if index_path is None:
        env_path = os.getenv(PATTERN_PATH_ENV, "").strip()
        if env_path:
            candidate = Path(env_path)
            if candidate.is_dir():
                candidate = candidate / "index.json"
            index_path = candidate
        else:
            index_path = DEFAULT_INDEX_PATH
    if not index_path.exists():
        raise Namel3ssError(
            build_guidance_message(
                what="Patterns index was not found.",
                why=f"Expected {index_path.as_posix()} to exist.",
                fix="Set N3_PATTERNS_PATH to a valid patterns directory.",
                example="N3_PATTERNS_PATH=./patterns",
            )
        )
    return index_path


def _read_index(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Patterns index is not valid JSON.",
                why=f"JSON parsing failed: {err.msg}.",
                fix="Fix the JSON formatting.",
                example="patterns/index.json",
            )
        ) from err


def _validate_index(data: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["index must be a JSON object"]
    if data.get("schema_version") != PATTERN_SCHEMA_VERSION:
        errors.append("schema_version must be 1")
    patterns = data.get("patterns")
    if not isinstance(patterns, list):
        return errors + ["patterns must be a list"]
    for idx, entry in enumerate(patterns, start=1):
        if not isinstance(entry, dict):
            errors.append(f"pattern {idx} must be an object")
            continue
        errors.extend(_validate_entry(entry, idx))
    return errors


def _validate_entry(entry: dict, idx: int) -> list[str]:
    errors: list[str] = []
    required = {"id", "description"}
    missing = required - set(entry.keys())
    if missing:
        errors.append(f"pattern {idx} missing fields: {', '.join(sorted(missing))}")
        return errors
    for key in ("id", "description"):
        value = entry.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"pattern {idx} {key} must be a non-empty string")
    path_value = entry.get("path")
    if path_value is not None and (not isinstance(path_value, str) or not path_value.strip()):
        errors.append(f"pattern {idx} path must be a non-empty string")
    return errors


__all__ = ["PATTERN_PATH_ENV", "PatternEntry", "get_pattern", "load_patterns"]
