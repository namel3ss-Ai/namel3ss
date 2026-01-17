from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.runtime.packs.layout import local_packs_root
from namel3ss.runtime.packs.pack_manifest import PackContents, load_pack_contents


@dataclass(frozen=True)
class PackLoadItem:
    pack_dir: Path
    contents: PackContents
    source: str


def load_local_pack_items(app_root: Path) -> list[PackLoadItem]:
    root = local_packs_root(app_root)
    if not root.exists():
        return []
    if not root.is_dir():
        return []
    items: list[PackLoadItem] = []
    for pack_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        contents = load_pack_contents(pack_dir)
        items.append(PackLoadItem(pack_dir=pack_dir, contents=contents, source="local_pack"))
    return items


__all__ = ["PackLoadItem", "load_local_pack_items"]
