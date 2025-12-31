from __future__ import annotations

import os
from pathlib import Path

from namel3ss.cli.demo_support import is_clearorders_demo

_TRUTHY = {"1", "true", "yes"}


def is_first_run(project_root: Path | None, args: list[str]) -> bool:
    if _has_first_run_flag(args):
        return True
    if _env_first_run():
        return True
    root = project_root or Path.cwd()
    if root and is_clearorders_demo(root):
        return True
    return False


def _has_first_run_flag(args: list[str]) -> bool:
    return any(arg == "--first-run" for arg in args)


def _env_first_run() -> bool:
    value = os.getenv("N3_FIRST_RUN", "")
    return value.strip().lower() in _TRUTHY


__all__ = ["is_first_run"]
