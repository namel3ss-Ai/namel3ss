from __future__ import annotations

import json
from pathlib import Path

DEMO_MARKER = ".namel3ss/demo.json"
DEMO_NAME = "demo"


def load_demo_marker(project_root: Path) -> dict | None:
    marker_path = Path(project_root) / DEMO_MARKER
    if not marker_path.exists():
        return None
    try:
        return json.loads(marker_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def is_demo_project(project_root: Path) -> bool:
    marker = load_demo_marker(project_root)
    if not marker:
        return False
    name = str(marker.get("name", ""))
    return name.lower() == DEMO_NAME.lower()


__all__ = ["DEMO_MARKER", "DEMO_NAME", "is_demo_project", "load_demo_marker"]
