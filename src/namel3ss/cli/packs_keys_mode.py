from __future__ import annotations

from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.trust_store import TrustedKey, add_trusted_key, load_trusted_keys
from namel3ss.utils.json_tools import dumps_pretty


def run_packs_keys(args: list[str], *, json_mode: bool) -> int:
    if not args or args[0] in {"help", "-h", "--help"}:
        _print_usage()
        return 0
    cmd = args[0]
    tail = args[1:]
    if cmd == "add":
        key_id, key_path = _parse_add_args(tail)
        app_path = resolve_app_path(None)
        app_root = app_path.parent
        key_text = Path(key_path).read_text(encoding="utf-8").strip()
        if not key_text:
            raise Namel3ssError(_invalid_key_file_message(key_path))
        path = add_trusted_key(app_root, TrustedKey(key_id=key_id, public_key=key_text))
        payload = {"status": "ok", "key_id": key_id, "keys_path": str(path)}
        if json_mode:
            print(dumps_pretty(payload))
            return 0
        print(f"Added trusted key '{key_id}'.")
        return 0
    if cmd == "list":
        if tail:
            raise Namel3ssError(_unknown_args_message(tail))
        app_path = resolve_app_path(None)
        app_root = app_path.parent
        keys = load_trusted_keys(app_root)
        payload = {"status": "ok", "trusted_keys": [key.__dict__ for key in keys]}
        if json_mode:
            print(dumps_pretty(payload))
            return 0
        print(f"Trusted keys: {len(keys)}")
        for key in keys:
            print(f"- {key.key_id}: {key.public_key}")
        return 0
    raise Namel3ssError(_unknown_command_message(cmd))


def _parse_add_args(args: list[str]) -> tuple[str, str]:
    key_id = None
    key_path = None
    idx = 0
    while idx < len(args):
        item = args[idx]
        if item == "--id":
            if idx + 1 >= len(args):
                raise Namel3ssError(_missing_flag_message("--id"))
            key_id = args[idx + 1]
            idx += 2
            continue
        if item.startswith("--id="):
            key_id = item.split("=", 1)[1]
            idx += 1
            continue
        if item == "--public-key":
            if idx + 1 >= len(args):
                raise Namel3ssError(_missing_flag_message("--public-key"))
            key_path = args[idx + 1]
            idx += 2
            continue
        if item.startswith("--public-key="):
            key_path = item.split("=", 1)[1]
            idx += 1
            continue
        raise Namel3ssError(_unknown_args_message([item]))
    if not key_id or not key_path:
        raise Namel3ssError(_missing_key_fields_message())
    return key_id, key_path


def _print_usage() -> None:
    usage = """Usage:
  n3 packs keys add --id id --public-key path --json
  n3 packs keys list --json
  Notes:
    flags are optional unless stated
"""
    print(usage.strip())


def _unknown_command_message(cmd: str) -> str:
    return build_guidance_message(
        what=f"Unknown packs keys command '{cmd}'.",
        why="Supported commands are add and list.",
        fix="Use `n3 packs keys add` or `n3 packs keys list`.",
        example="n3 packs keys list",
    )


def _unknown_args_message(args: list[str]) -> str:
    return build_guidance_message(
        what=f"Unknown arguments: {' '.join(args)}.",
        why="n3 packs keys add only accepts --id and --public-key.",
        fix="Remove extra arguments.",
        example='n3 packs keys add --id "maintainer.alice" --public-key ./alice.pub',
    )


def _missing_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Missing value for {flag}.",
        why="The flag expects a value.",
        fix="Provide a value after the flag.",
        example=f"{flag} VALUE",
    )


def _missing_key_fields_message() -> str:
    return build_guidance_message(
        what="Key id or public key path is missing.",
        why="You must provide both --id and --public-key.",
        fix="Pass both flags with values.",
        example='n3 packs keys add --id "maintainer.alice" --public-key ./alice.pub',
    )


def _invalid_key_file_message(path: str) -> str:
    return build_guidance_message(
        what="Public key file is empty.",
        why=f"No data found in {path}.",
        fix="Provide a valid key file.",
        example='n3 packs keys add --id "maintainer.alice" --public-key ./alice.pub',
    )


__all__ = ["run_packs_keys"]
