from __future__ import annotations

from typing import Dict

from namel3ss.errors.base import Namel3ssError


def execute_tool(name: str, args: Dict[str, object]) -> Dict[str, object]:
    if name == "echo":
        if not isinstance(args, dict):
            raise Namel3ssError("Tool args must be a dictionary")
        return {"echo": args}
    raise Namel3ssError(f"Unknown tool '{name}'")
