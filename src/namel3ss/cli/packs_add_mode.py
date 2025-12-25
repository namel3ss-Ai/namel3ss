from __future__ import annotations

from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.ops import install_pack
from namel3ss.runtime.registry.ops import install_pack_from_registry
from namel3ss.utils.json_tools import dumps_pretty


def run_packs_add(args: list[str], *, json_mode: bool) -> int:
    if not args:
        raise Namel3ssError(_missing_path_message())
    target = None
    registry_id = None
    idx = 0
    while idx < len(args):
        item = args[idx]
        if item == "--from":
            registry_id = _next_value(args, idx, "--from")
            idx += 2
            continue
        if item.startswith("--"):
            raise Namel3ssError(_unknown_args_message([item]))
        if target is None:
            target = item
            idx += 1
            continue
        raise Namel3ssError(_unknown_args_message([item]))
    if not target:
        raise Namel3ssError(_missing_path_message())
    source = Path(target).expanduser().resolve()
    app_path = resolve_app_path(None)
    app_root = app_path.parent
    if registry_id or (not source.exists() and "@" in target):
        if source.exists():
            raise Namel3ssError(_registry_path_message())
        pack_id, pack_version = _parse_pack_ref(target)
        config = load_config(root=app_root)
        pack_id = pack_id.strip()
        installed_id, bundle_path = install_pack_from_registry(
            app_root,
            config,
            pack_id=pack_id,
            pack_version=pack_version,
            registry_id=registry_id,
        )
        payload = {"status": "ok", "pack_id": installed_id, "bundle_path": str(bundle_path)}
        if json_mode:
            print(dumps_pretty(payload))
            return 0
        print(f"Installed pack '{installed_id}' from registry.")
        return 0
    if not source.exists():
        raise Namel3ssError(_missing_path_message())
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
        why="You must provide a pack path or pack_id@version.",
        fix="Pass a pack path or pack_id@version to install.",
        example="n3 packs add team.pack@0.1.0",
    )


def _unknown_args_message(args: list[str]) -> str:
    joined = " ".join(args)
    return build_guidance_message(
        what=f"Unknown arguments: {joined}.",
        why="n3 packs add accepts a single path or pack_id@version.",
        fix="Remove the extra arguments and try again.",
        example="n3 packs add ./my_pack",
    )


def _registry_path_message() -> str:
    return build_guidance_message(
        what="Pack path cannot be used with --from.",
        why="--from is only valid for pack_id@version installs.",
        fix="Remove --from or use pack_id@version.",
        example="n3 packs add team.pack@0.1.0 --from local",
    )


def _parse_pack_ref(value: str) -> tuple[str, str]:
    if "@" not in value:
        raise Namel3ssError(_missing_version_message())
    pack_id, version = value.rsplit("@", 1)
    if not pack_id or not version:
        raise Namel3ssError(_missing_version_message())
    return pack_id, version


def _missing_version_message() -> str:
    return build_guidance_message(
        what="Pack version is missing.",
        why="Pack ids must include a version for registry installs.",
        fix="Use pack_id@version.",
        example="n3 packs add team.pack@0.1.0",
    )


def _next_value(args: list[str], idx: int, flag: str) -> str:
    if idx + 1 >= len(args):
        raise Namel3ssError(_missing_flag_message(flag))
    value = args[idx + 1]
    if not value or value.startswith("--"):
        raise Namel3ssError(_missing_flag_message(flag))
    return value


def _missing_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"{flag} is missing a value.",
        why="Flags must be followed by a value.",
        fix=f"Provide a value after {flag}.",
        example=f"{flag} local",
    )


__all__ = ["run_packs_add"]
