from __future__ import annotations

from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.ops import install_pack
from namel3ss.utils.json_tools import dumps_pretty


def run_packs_add(args: list[str], *, json_mode: bool) -> int:
    if not args:
        raise Namel3ssError(_missing_path_message())
    if len(args) > 1:
        raise Namel3ssError(_unknown_args_message(args[1:]))
    source = Path(args[0]).expanduser().resolve()
    if not source.exists():
        raise Namel3ssError(_missing_path_message())
    app_path = resolve_app_path(None)
    app_root = app_path.parent
    pack_id = install_pack(app_root, source)
    payload = {"status": "ok", "pack_id": pack_id, "pack_path": str(app_root / ".namel3ss" / "packs" / pack_id)}
    if json_mode:
        print(dumps_pretty(payload))
        return 0
    print(f"Installed pack '{pack_id}'.")
    print(f"Pack path: {payload['pack_path']}")
    return 0


def _missing_path_message() -> str:
    return build_guidance_message(
        what="Pack source path is missing.",
        why="You must provide a pack folder or zip path.",
        fix="Pass a pack path to install.",
        example="n3 packs add ./my_pack",
    )


def _unknown_args_message(args: list[str]) -> str:
    joined = " ".join(args)
    return build_guidance_message(
        what=f"Unknown arguments: {joined}.",
        why="n3 packs add accepts a single path.",
        fix="Remove the extra arguments and try again.",
        example="n3 packs add ./my_pack",
    )


__all__ = ["run_packs_add"]
