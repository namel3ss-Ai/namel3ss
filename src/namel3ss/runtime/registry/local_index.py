from __future__ import annotations

import json
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.registry.entry import RegistryEntry
from namel3ss.runtime.registry.layout import registry_compact_path, registry_index_path


def append_registry_entry(app_root: Path, entry: RegistryEntry) -> Path:
    path = registry_index_path(app_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(entry.to_dict(), sort_keys=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(payload + "\n")
    return path


def load_registry_entries(app_root: Path) -> list[dict[str, object]]:
    index_path = registry_index_path(app_root)
    compact_path = registry_compact_path(app_root)
    return load_registry_entries_from_path(index_path, compact_path)


def build_compact_index(app_root: Path) -> Path:
    index_path = registry_index_path(app_root)
    compact_path = registry_compact_path(app_root)
    return build_compact_index_from_path(index_path, compact_path)


def load_registry_entries_from_path(index_path: Path, compact_path: Path | None = None) -> list[dict[str, object]]:
    if compact_path and compact_path.exists():
        return _load_compact(compact_path)
    if not index_path.exists():
        return []
    return _load_jsonl(index_path)


def build_compact_index_from_path(index_path: Path, compact_path: Path) -> Path:
    entries = _load_jsonl(index_path) if index_path.exists() else []
    deduped: dict[str, dict[str, object]] = {}
    for entry in entries:
        key = _entry_key(entry)
        if key:
            deduped[key] = entry
    sorted_entries = sorted(deduped.values(), key=_sort_key)
    payload = {"entries": sorted_entries}
    compact_path.parent.mkdir(parents=True, exist_ok=True)
    compact_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return compact_path


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as err:
            raise Namel3ssError(_invalid_registry_message(path, err.msg)) from err
        if isinstance(item, dict):
            entries.append(item)
    return entries


def _load_compact(path: Path) -> list[dict[str, object]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise Namel3ssError(_invalid_registry_message(path, err.msg)) from err
    if isinstance(data, dict):
        entries = data.get("entries")
        if isinstance(entries, list):
            return [entry for entry in entries if isinstance(entry, dict)]
    if isinstance(data, list):
        return [entry for entry in data if isinstance(entry, dict)]
    return []


def _entry_key(entry: dict[str, object]) -> str | None:
    pack_id = entry.get("pack_id")
    version = entry.get("pack_version")
    digest = entry.get("pack_digest")
    if not isinstance(pack_id, str) or not isinstance(version, str) or not isinstance(digest, str):
        return None
    return f"{pack_id}@{version}:{digest}"


def _sort_key(entry: dict[str, object]) -> tuple[str, str, str]:
    pack_id = entry.get("pack_id") if isinstance(entry.get("pack_id"), str) else ""
    version = entry.get("pack_version") if isinstance(entry.get("pack_version"), str) else ""
    digest = entry.get("pack_digest") if isinstance(entry.get("pack_digest"), str) else ""
    return (pack_id, version, digest)


def _invalid_registry_message(path: Path, details: str) -> str:
    return build_guidance_message(
        what="Registry index is invalid.",
        why=f"{path.as_posix()} could not be parsed: {details}.",
        fix="Rebuild the registry index.",
        example="n3 registry build",
    )


__all__ = [
    "append_registry_entry",
    "build_compact_index",
    "build_compact_index_from_path",
    "load_registry_entries",
    "load_registry_entries_from_path",
]
