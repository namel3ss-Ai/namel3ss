from __future__ import annotations

from pathlib import Path

from namel3ss.utils.simple_yaml import parse_yaml, render_yaml


CAPABILITIES_FILE = "capabilities.yaml"
MARKETPLACE_KEY = "marketplace_items"


def record_installed_item(
    project_root: Path,
    *,
    name: str,
    version: str,
    item_type: str,
    files: list[str],
) -> Path:
    path = project_root / CAPABILITIES_FILE
    payload: dict[str, object] = {}
    if path.exists():
        parsed = parse_yaml(path.read_text(encoding="utf-8"))
        if isinstance(parsed, dict):
            payload = dict(parsed)
    existing = payload.get(MARKETPLACE_KEY)
    items: list[dict[str, object]] = []
    if isinstance(existing, list):
        for entry in existing:
            if not isinstance(entry, dict):
                continue
            entry_name = str(entry.get("name") or "")
            entry_version = str(entry.get("version") or "")
            if entry_name == name and entry_version == version:
                continue
            items.append(
                {
                    "name": entry_name,
                    "version": entry_version,
                    "type": str(entry.get("type") or ""),
                    "files": _normalize_files(entry.get("files")),
                }
            )
    items.append(
        {
            "name": name,
            "version": version,
            "type": item_type,
            "files": sorted({part.strip().replace("\\", "/") for part in files if part and part.strip()}),
        }
    )
    items.sort(key=lambda item: (str(item.get("name") or ""), str(item.get("version") or "")))
    payload[MARKETPLACE_KEY] = items
    path.write_text(render_yaml(payload), encoding="utf-8")
    return path


def _normalize_files(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized = [str(item).strip().replace("\\", "/") for item in value if isinstance(item, str) and str(item).strip()]
    return sorted(set(normalized))


__all__ = ["CAPABILITIES_FILE", "MARKETPLACE_KEY", "record_installed_item"]
