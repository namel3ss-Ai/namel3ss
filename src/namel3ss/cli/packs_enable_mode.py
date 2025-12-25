from __future__ import annotations

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.ops import enable_pack
from namel3ss.runtime.packs.registry import load_pack_registry
from namel3ss.utils.json_tools import dumps_pretty


def run_packs_enable(args: list[str], *, json_mode: bool) -> int:
    if not args:
        raise Namel3ssError(_missing_pack_message())
    pack_id = args[0]
    if len(args) > 1:
        raise Namel3ssError(_unknown_args_message(args[1:]))
    app_path = resolve_app_path(None)
    app_root = app_path.parent
    config = load_config(root=app_root)
    registry = load_pack_registry(app_root, config)
    pack = registry.packs.get(pack_id)
    if not pack:
        raise Namel3ssError(_pack_missing_message(pack_id))
    if not pack.verified:
        raise Namel3ssError(_pack_unverified_message(pack_id))
    path = enable_pack(app_root, pack_id)
    payload = {"status": "ok", "pack_id": pack_id, "config_path": str(path)}
    if json_mode:
        print(dumps_pretty(payload))
        return 0
    print(f"Enabled pack '{pack_id}'.")
    return 0


def _missing_pack_message() -> str:
    return build_guidance_message(
        what="Pack id is missing.",
        why="You must specify which pack to enable.",
        fix="Provide a pack id.",
        example="n3 packs enable pack.slug",
    )


def _unknown_args_message(args: list[str]) -> str:
    joined = " ".join(args)
    return build_guidance_message(
        what=f"Unknown arguments: {joined}.",
        why="n3 packs enable accepts a pack id only.",
        fix="Remove the extra arguments.",
        example="n3 packs enable pack.slug",
    )


def _pack_missing_message(pack_id: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" was not found.',
        why="The pack is not installed.",
        fix="Install the pack before enabling it.",
        example=f"n3 packs add ./packs/{pack_id}",
    )


def _pack_unverified_message(pack_id: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" is unverified.',
        why="Unverified packs cannot be enabled by default.",
        fix="Verify the pack before enabling it.",
        example=f"n3 packs verify {pack_id}",
    )


__all__ = ["run_packs_enable"]
