from __future__ import annotations

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.registry.ops import build_registry_index
from namel3ss.utils.json_tools import dumps_pretty


def run_registry_build(args: list[str], *, json_mode: bool) -> int:
    if args:
        raise Namel3ssError(_unknown_args_message(args))
    app_path = resolve_app_path(None)
    app_root = app_path.parent
    config = load_config(root=app_root)
    compact_path = build_registry_index(app_root, config)
    payload = {"status": "ok", "index_path": str(compact_path)}
    if json_mode:
        print(dumps_pretty(payload))
        return 0
    print(f"Registry index built: {compact_path}")
    return 0


def _unknown_args_message(args: list[str]) -> str:
    return build_guidance_message(
        what=f"Unknown arguments: {' '.join(args)}.",
        why="n3 registry build does not accept positional arguments.",
        fix="Remove the extra arguments.",
        example="n3 registry build",
    )


__all__ = ["run_registry_build"]
