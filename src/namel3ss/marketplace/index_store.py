from __future__ import annotations

import json
from pathlib import Path

from namel3ss.determinism import canonical_json_dumps


INDEX_FILE = "index.jsonl"
RATINGS_FILE = "ratings.jsonl"



def load_index_entries(registry_root: Path) -> list[dict[str, object]]:
    path = registry_root / INDEX_FILE
    if not path.exists():
        return []
    entries: list[dict[str, object]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            entries.append(item)
    return entries



def write_index_entries(registry_root: Path, entries: list[dict[str, object]]) -> None:
    path = registry_root / INDEX_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = [
        {
            "name": str(entry.get("name") or ""),
            "version": str(entry.get("version") or ""),
            "type": str(entry.get("type") or ""),
            "description": str(entry.get("description") or ""),
            "author": str(entry.get("author") or ""),
            "license": str(entry.get("license") or ""),
            "files": sorted(set(str(item) for item in (entry.get("files") or []) if isinstance(item, str))),
            "dependencies": sorted(set(str(item) for item in (entry.get("dependencies") or []) if isinstance(item, str))),
            "bundle": str(entry.get("bundle") or ""),
            "digest": str(entry.get("digest") or ""),
            "status": str(entry.get("status") or "pending_review"),
            "rating_count": int(entry.get("rating_count") or 0),
            "rating_avg": float(entry.get("rating_avg") or 0.0),
        }
        for entry in entries
    ]
    deduped: dict[str, dict[str, object]] = {}
    for item in normalized:
        deduped[item_key(str(item["name"]), str(item["version"]))] = item
    ordered = sorted(deduped.values(), key=lambda item: (str(item["name"]), version_sort_value(str(item["version"]))))
    lines = [canonical_json_dumps(item, pretty=False, drop_run_keys=False) for item in ordered]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")



def load_ratings(registry_root: Path) -> list[dict[str, object]]:
    path = registry_root / RATINGS_FILE
    if not path.exists():
        return []
    rows: list[dict[str, object]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows



def write_ratings(registry_root: Path, ratings: list[dict[str, object]]) -> None:
    path = registry_root / RATINGS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in ratings:
        rows.append(
            {
                "name": str(item.get("name") or ""),
                "version": str(item.get("version") or ""),
                "rating": int(item.get("rating") or 0),
                "comment": str(item.get("comment") or ""),
            }
        )
    rows.sort(key=lambda item: (item["name"], version_sort_value(item["version"]), item["rating"], item["comment"]))
    lines = [canonical_json_dumps(item, pretty=False, drop_run_keys=False) for item in rows]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")



def ratings_aggregate(ratings: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[int]] = {}
    for entry in ratings:
        name = str(entry.get("name") or "")
        version = str(entry.get("version") or "")
        rating = int(entry.get("rating") or 0)
        if not name or not version or rating < 1 or rating > 5:
            continue
        grouped.setdefault(item_key(name, version), []).append(rating)
    result: dict[str, dict[str, object]] = {}
    for key, values in grouped.items():
        result[key] = {
            "count": len(values),
            "avg": float(sum(values) / len(values)),
        }
    return result



def item_key(name: str, version: str) -> str:
    return f"{name}@{version}"



def same_item(entry: dict[str, object], name: str, version: str) -> bool:
    return str(entry.get("name") or "") == name and str(entry.get("version") or "") == version



def version_sort_value(version: str) -> tuple[int, ...]:
    pieces = version.split(".")
    parsed: list[int] = []
    for piece in pieces:
        if piece.isdigit():
            parsed.append(int(piece))
        else:
            parsed.append(0)
    return tuple(parsed)


__all__ = [
    "INDEX_FILE",
    "RATINGS_FILE",
    "item_key",
    "load_index_entries",
    "load_ratings",
    "ratings_aggregate",
    "same_item",
    "version_sort_value",
    "write_index_entries",
    "write_ratings",
]
