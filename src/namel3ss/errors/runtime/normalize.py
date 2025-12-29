from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from namel3ss.errors.runtime.model import ErrorPack, Namel3ssRuntimeError
from namel3ss.secrets import redact_payload, redact_text


_MAX_TRACE_ENTRIES = 10
_MAX_TEXT = 200
_TIME_KEYS = {"timestamp", "time", "time_start", "time_end", "duration_ms"}
_ID_KEYS = {"call_id", "tool_call_id"}


def normalize_error(err: Namel3ssRuntimeError) -> Namel3ssRuntimeError:
    return Namel3ssRuntimeError(
        error_id=err.error_id,
        kind=err.kind,
        boundary=err.boundary,
        what=stable_truncate(err.what, _MAX_TEXT),
        why=normalize_bullets(err.why),
        fix=normalize_bullets(err.fix),
        example=stable_truncate(err.example, _MAX_TEXT) if err.example else None,
        where=err.where,
        raw_message=stable_truncate(err.raw_message, _MAX_TEXT),
    )


def normalize_bullets(items: Iterable[str]) -> tuple[str, ...]:
    cleaned: list[str] = []
    for item in items:
        text = " ".join(str(item).split())
        text = stable_truncate(text.strip(), _MAX_TEXT)
        if text:
            cleaned.append(text)
    return tuple(sorted(set(cleaned)))


def normalize_traces(traces: list[dict] | None, *, secret_values: list[str]) -> list[dict]:
    if not traces:
        return []
    tail = traces[-_MAX_TRACE_ENTRIES:]
    normalized: list[dict] = []
    for entry in tail:
        if not isinstance(entry, dict):
            continue
        redacted = redact_payload(entry, secret_values)
        normalized.append(_normalize_mapping(redacted))
    return normalized


def write_error_artifacts(root: Path, pack: ErrorPack, plain_text: str, fix_text: str) -> None:
    errors_dir = root / ".namel3ss" / "errors"
    errors_dir.mkdir(parents=True, exist_ok=True)
    (errors_dir / "last.json").write_text(_stable_json(pack.as_dict()), encoding="utf-8")
    (errors_dir / "last.plain").write_text(plain_text.rstrip() + "\n", encoding="utf-8")
    (errors_dir / "last.fix.txt").write_text(fix_text.rstrip() + "\n", encoding="utf-8")

    history_dir = errors_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    error_id = pack.error.error_id
    if error_id:
        (history_dir / f"{error_id}.json").write_text(_stable_json(pack.as_dict()), encoding="utf-8")


def stable_truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _normalize_mapping(value: object) -> dict:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, object] = {}
    for key in sorted(value.keys()):
        normalized[key] = _normalize_value(key, value[key])
    return normalized


def _normalize_value(key: str, value: object) -> object:
    if key in _TIME_KEYS:
        return "<time>"
    if key in _ID_KEYS:
        return "<id>"
    if isinstance(value, dict):
        return _normalize_mapping(value)
    if isinstance(value, list):
        return [_normalize_value("", item) for item in value]
    if isinstance(value, str):
        return redact_text(value, [])
    return value


def _stable_json(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


__all__ = [
    "normalize_error",
    "normalize_bullets",
    "normalize_traces",
    "stable_truncate",
    "write_error_artifacts",
]
