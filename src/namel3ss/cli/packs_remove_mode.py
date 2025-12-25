from __future__ import annotations

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.ops import remove_pack
from namel3ss.utils.json_tools import dumps_pretty


def run_packs_remove(args: list[str], *, json_mode: bool) -> int:
    if not args:
        raise Namel3ssError(_missing_pack_message())
    pack_id = args[0]
    if "--yes" not in args[1:]:
        raise Namel3ssError(_missing_yes_message(pack_id))
    app_path = resolve_app_path(None)
    app_root = app_path.parent
    path = remove_pack(app_root, pack_id)
    payload = {"status": "ok", "pack_id": pack_id, "pack_path": str(path)}
    if json_mode:
        print(dumps_pretty(payload))
        return 0
    print(f"Removed pack '{pack_id}'.")
    return 0


def _missing_pack_message() -> str:
    return build_guidance_message(
        what="Pack id is missing.",
        why="You must specify which pack to remove.",
        fix="Provide a pack id.",
        example="n3 packs remove pack.slug --yes",
    )


def _missing_yes_message(pack_id: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" removal requires confirmation.',
        why="Removing packs deletes files from .namel3ss/packs.",
        fix="Re-run with --yes to confirm.",
        example=f"n3 packs remove {pack_id} --yes",
    )


__all__ = ["run_packs_remove"]
