from __future__ import annotations

import json
from pathlib import Path

from namel3ss.tools_with.model import ToolsWithPack


def stable_sort(entries: list[dict]) -> list[dict]:
    return sorted(
        entries,
        key=lambda item: (
            str(item.get("tool") or ""),
            str(item.get("decision") or ""),
            str(item.get("reason") or ""),
        ),
    )


def write_tools_with_artifacts(root: Path, pack: ToolsWithPack, plain: str, text: str) -> None:
    tools_dir = root / ".namel3ss" / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    payload = pack.as_dict()
    (tools_dir / "last.json").write_text(_stable_json(payload), encoding="utf-8")
    (tools_dir / "last.plain").write_text(plain.rstrip() + "\n", encoding="utf-8")
    (tools_dir / "last.with.txt").write_text(text.rstrip() + "\n", encoding="utf-8")


def _stable_json(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, indent=2) + "\n"


__all__ = ["stable_sort", "write_tools_with_artifacts"]
