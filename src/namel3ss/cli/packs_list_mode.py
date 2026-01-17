from __future__ import annotations

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.registry import load_pack_registry, pack_payload
from namel3ss.utils.json_tools import dumps_pretty


def run_packs_list(args: list[str], *, json_mode: bool) -> int:
    if args:
        raise Namel3ssError(_unknown_args_message(args))
    app_path = resolve_app_path(None)
    app_root = app_path.parent
    config = load_config(root=app_root)
    registry = load_pack_registry(app_root, config)
    packs = [pack for pack in registry.packs.values()]
    payload = {
        "packs": [pack_payload(pack) for pack in sorted(packs, key=lambda item: item.pack_id)],
    }
    if json_mode:
        print(dumps_pretty(payload))
        return 0
    print(f"Packs available: {len(packs)}")
    for pack in sorted(packs, key=lambda item: item.pack_id):
        status = "enabled" if pack.enabled else "disabled"
        verify = "verified" if pack.verified else "unverified"
        source = _source_label(pack.source)
        line = f"- {pack.pack_id} ({pack.name}) source {source} status {status} verify {verify}"
        print(line)
    return 0


def _unknown_args_message(args: list[str]) -> str:
    joined = " ".join(args)
    return build_guidance_message(
        what=f"Unknown arguments: {joined}.",
        why="n3 pack list does not accept positional arguments.",
        fix="Remove the extra arguments.",
        example="n3 pack list",
    )


def _source_label(source: str) -> str:
    if source == "builtin_pack":
        return "builtin"
    if source == "installed_pack":
        return "installed"
    if source == "local_pack":
        return "local"
    return source


__all__ = ["run_packs_list"]
