from __future__ import annotations

from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.authoring_paths import resolve_pack_dir
from namel3ss.runtime.packs.authoring_sign import sign_pack
from namel3ss.utils.json_tools import dumps_pretty


def run_packs_sign(args: list[str], *, json_mode: bool) -> int:
    if not args or args[0] in {"help", "-h", "--help"}:
        _print_usage()
        return 0
    target = None
    key_id = None
    private_key = None
    idx = 0
    while idx < len(args):
        item = args[idx]
        if item == "--key-id":
            if idx + 1 >= len(args):
                raise Namel3ssError(_missing_flag_message("--key-id"))
            key_id = args[idx + 1]
            idx += 2
            continue
        if item.startswith("--key-id="):
            key_id = item.split("=", 1)[1]
            idx += 1
            continue
        if item == "--private-key":
            if idx + 1 >= len(args):
                raise Namel3ssError(_missing_flag_message("--private-key"))
            private_key = args[idx + 1]
            idx += 2
            continue
        if item.startswith("--private-key="):
            private_key = item.split("=", 1)[1]
            idx += 1
            continue
        if target is None:
            target = item
            idx += 1
            continue
        raise Namel3ssError(_unknown_args_message([item]))
    if not target:
        raise Namel3ssError(_missing_target_message())
    if not key_id or not private_key:
        raise Namel3ssError(_missing_key_fields_message())
    pack_dir = _resolve_pack_dir(target)
    result = sign_pack(pack_dir, key_id=key_id, private_key_path=Path(private_key))
    payload = {
        "status": "ok",
        "pack_id": result.pack_id,
        "version": result.version,
        "digest": result.digest,
        "signer_id": result.signer_id,
        "signed_at": result.signed_at,
        "signature_path": str(result.signature_path),
        "manifest_path": str(result.manifest_path),
    }
    if json_mode:
        print(dumps_pretty(payload))
        return 0
    print(f"Pack signed: {result.pack_id} digest {result.digest}")
    return 0


def _print_usage() -> None:
    usage = """Usage:
  n3 packs sign path_or_pack --key-id id --private-key path --json
  Notes:
    flags are optional unless stated
"""
    print(usage.strip())


def _resolve_pack_dir(value: str) -> Path:
    path = Path(value)
    if path.exists():
        return path
    app_path = resolve_app_path(None)
    return resolve_pack_dir(app_path.parent, value)


def _missing_target_message() -> str:
    return build_guidance_message(
        what="Pack target is missing.",
        why="You must provide a path or pack id.",
        fix="Pass a pack directory or pack id.",
        example='n3 packs sign ./pack --key-id "maintainer.alice" --private-key ./alice.key',
    )


def _missing_key_fields_message() -> str:
    return build_guidance_message(
        what="Signer metadata is incomplete.",
        why="You must provide --key-id and --private-key.",
        fix="Pass both signer flags with values.",
        example='n3 packs sign ./pack --key-id "maintainer.alice" --private-key ./alice.key',
    )


def _unknown_args_message(args: list[str]) -> str:
    return build_guidance_message(
        what=f"Unknown arguments: {' '.join(args)}.",
        why="n3 packs sign accepts --key-id and --private-key.",
        fix="Remove the extra arguments.",
        example='n3 packs sign ./pack --key-id "maintainer.alice" --private-key ./alice.key',
    )


def _missing_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Missing value for {flag}.",
        why="The flag expects a value.",
        fix="Provide a value after the flag.",
        example=f"{flag} VALUE",
    )


__all__ = ["run_packs_sign"]
