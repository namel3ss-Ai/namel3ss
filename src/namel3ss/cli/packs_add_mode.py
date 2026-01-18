from __future__ import annotations

from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.ops import install_pack
from namel3ss.runtime.registry.ops import install_pack_from_registry
from namel3ss.utils.path_display import display_path_hint
from namel3ss.utils.json_tools import dumps_pretty


def run_packs_add(args: list[str], *, json_mode: bool) -> int:
    if not args:
        raise Namel3ssError(_missing_path_message())
    target = None
    registry_id = None
    registry_url = None
    offline = False
    idx = 0
    while idx < len(args):
        item = args[idx]
        if item in {"--from", "--registry"}:
            value = _next_value(args, idx, item)
            registry_id, registry_url = _assign_registry(value, registry_id, registry_url)
            idx += 2
            continue
        if item.startswith("--from=") or item.startswith("--registry="):
            value = item.split("=", 1)[1]
            registry_id, registry_url = _assign_registry(value, registry_id, registry_url)
            idx += 1
            continue
        if item == "--offline":
            offline = True
            idx += 1
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
    if source.exists():
        if registry_id or registry_url:
            raise Namel3ssError(_registry_path_message())
        pack_id = install_pack(app_root, source)
        pack_path = app_root / ".namel3ss" / "packs" / pack_id
        payload = {
            "status": "ok",
            "pack_id": pack_id,
            "pack_path": display_path_hint(pack_path, base=Path.cwd()),
        }
        if json_mode:
            print(dumps_pretty(payload))
            return 0
        print(f"Installed pack '{pack_id}'.")
        print(f"Pack path: {payload['pack_path']}")
        return 0
    pack_id, pack_version = _parse_pack_ref(target)
    config = load_config(root=app_root)
    pack_id = pack_id.strip()
    installed_id, bundle_path = install_pack_from_registry(
        app_root,
        config,
        pack_id=pack_id,
        pack_version=pack_version,
        registry_id=registry_id,
        registry_url=registry_url,
        offline=offline,
    )
    bundle_hint = display_path_hint(bundle_path, base=Path.cwd())
    payload = {"status": "ok", "pack_id": installed_id, "bundle_path": bundle_hint}
    if json_mode:
        print(dumps_pretty(payload))
        return 0
    print(f"Installed pack '{installed_id}' from registry.")
    return 0


def _missing_path_message() -> str:
    return build_guidance_message(
        what="Pack source path is missing.",
        why="You must provide a pack path or pack name.",
        fix="Pass a pack path or pack name to install.",
        example="n3 pack add team.pack",
    )


def _unknown_args_message(args: list[str]) -> str:
    joined = " ".join(args)
    return build_guidance_message(
        what=f"Unknown arguments: {joined}.",
        why="n3 pack add accepts a single path or pack name.",
        fix="Remove the extra arguments and try again.",
        example="n3 pack add ./my_pack",
    )


def _registry_path_message() -> str:
    return build_guidance_message(
        what="Pack path cannot be used with registry flags.",
        why="--registry is only valid for pack name installs.",
        fix="Remove --registry or use a pack name.",
        example="n3 pack add team.pack --registry local",
    )


def _parse_pack_ref(value: str) -> tuple[str, str | None]:
    if "@" not in value:
        return value, None
    pack_id, version = value.rsplit("@", 1)
    if not pack_id or not version:
        raise Namel3ssError(_missing_version_message())
    return pack_id, version


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


def _missing_version_message() -> str:
    return build_guidance_message(
        what="Pack reference is invalid.",
        why="Pack references with @ must include a version.",
        fix="Remove @ or provide a full reference.",
        example="n3 pack add team.pack",
    )


def _assign_registry(
    value: str,
    registry_id: str | None,
    registry_url: str | None,
) -> tuple[str | None, str | None]:
    if value.startswith("http://") or value.startswith("https://"):
        return registry_id, value
    return value, registry_url


__all__ = ["run_packs_add"]
