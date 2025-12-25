from __future__ import annotations

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.ops import verify_pack
from namel3ss.utils.json_tools import dumps_pretty


def run_packs_verify(args: list[str], *, json_mode: bool) -> int:
    if not args:
        raise Namel3ssError(_missing_pack_message())
    pack_id = args[0]
    if len(args) > 1:
        raise Namel3ssError(_unknown_args_message(args[1:]))
    app_path = resolve_app_path(None)
    app_root = app_path.parent
    verify_pack(app_root, pack_id)
    payload = {"status": "ok", "pack_id": pack_id}
    if json_mode:
        print(dumps_pretty(payload))
        return 0
    print(f"Verified pack '{pack_id}'.")
    return 0


def _missing_pack_message() -> str:
    return build_guidance_message(
        what="Pack id is missing.",
        why="You must specify which pack to verify.",
        fix="Provide a pack id.",
        example="n3 packs verify pack.slug",
    )


def _unknown_args_message(args: list[str]) -> str:
    joined = " ".join(args)
    return build_guidance_message(
        what=f"Unknown arguments: {joined}.",
        why="n3 packs verify accepts a pack id only.",
        fix="Remove the extra arguments.",
        example="n3 packs verify pack.slug",
    )


__all__ = ["run_packs_verify"]
