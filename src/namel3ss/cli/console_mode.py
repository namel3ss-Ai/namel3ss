from __future__ import annotations

from namel3ss.cli.studio_mode import run_studio



def run_console(path: str, port: int, dry: bool) -> int:
    return run_studio(path, port, dry)


__all__ = ["run_console"]
