from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.authoring_init import init_pack
from namel3ss.utils.json_tools import dumps_pretty


def run_packs_init(args: list[str], *, json_mode: bool) -> int:
    if not args or args[0] in {"help", "-h", "--help"}:
        _print_usage()
        return 0
    pack_id = args[0]
    tail = args[1:]
    target_dir = Path(".")
    no_code = False
    idx = 0
    while idx < len(tail):
        item = tail[idx]
        if item == "--no-code":
            no_code = True
            idx += 1
            continue
        if item == "--dir":
            if idx + 1 >= len(tail):
                raise Namel3ssError(_missing_flag_message("--dir"))
            target_dir = Path(tail[idx + 1])
            idx += 2
            continue
        if item.startswith("--dir="):
            target_dir = Path(item.split("=", 1)[1])
            idx += 1
            continue
        raise Namel3ssError(_unknown_args_message([item]))
    result = init_pack(pack_id, target_dir=target_dir, no_code=no_code)
    payload = {
        "status": "ok",
        "pack_id": result.pack_id,
        "path": str(result.path),
        "files": result.files,
        "no_code": result.no_code,
    }
    if json_mode:
        print(dumps_pretty(payload))
        return 0
    print(f"Pack initialized at {result.path.as_posix()}")
    return 0


def _print_usage() -> None:
    usage = """Usage:
  n3 packs init pack_id --dir path --no-code --json
  Notes:
    flags are optional unless stated
"""
    print(usage.strip())


def _unknown_args_message(args: list[str]) -> str:
    return build_guidance_message(
        what=f"Unknown arguments: {' '.join(args)}.",
        why="n3 packs init accepts --dir and --no-code.",
        fix="Remove the extra arguments.",
        example="n3 packs init team.pack --dir ./packs",
    )


def _missing_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Missing value for {flag}.",
        why="The flag expects a value.",
        fix="Provide a value after the flag.",
        example=f"{flag} ./packs",
    )


__all__ = ["run_packs_init"]
