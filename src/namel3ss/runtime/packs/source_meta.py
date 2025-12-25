from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from namel3ss.runtime.packs.layout import pack_source_meta_path


@dataclass(frozen=True)
class PackSourceInfo:
    source_type: str
    path: str


def read_pack_source(pack_dir: Path) -> PackSourceInfo | None:
    path = pack_source_meta_path(pack_dir)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    source_type = data.get("source_type")
    source_path = data.get("path")
    if not isinstance(source_type, str) or not isinstance(source_path, str):
        return None
    return PackSourceInfo(source_type=source_type, path=source_path)


def write_pack_source(pack_dir: Path, info: PackSourceInfo) -> Path:
    payload = {"source_type": info.source_type, "path": info.path}
    path = pack_source_meta_path(pack_dir)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


__all__ = ["PackSourceInfo", "read_pack_source", "write_pack_source"]
