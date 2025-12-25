from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def run_packs(args: list[str]) -> int:
    if not args or args[0] in {"help", "-h", "--help"}:
        _print_usage()
        return 0
    cmd = args[0]
    tail = args[1:]
    json_mode = "--json" in tail
    tail = [item for item in tail if item != "--json"]
    if cmd == "add":
        from namel3ss.cli.packs_add_mode import run_packs_add

        return run_packs_add(tail, json_mode=json_mode)
    if cmd == "remove":
        from namel3ss.cli.packs_remove_mode import run_packs_remove

        return run_packs_remove(tail, json_mode=json_mode)
    if cmd == "status":
        from namel3ss.cli.packs_status_mode import run_packs_status

        return run_packs_status(tail, json_mode=json_mode)
    if cmd == "verify":
        from namel3ss.cli.packs_verify_mode import run_packs_verify

        return run_packs_verify(tail, json_mode=json_mode)
    if cmd == "enable":
        from namel3ss.cli.packs_enable_mode import run_packs_enable

        return run_packs_enable(tail, json_mode=json_mode)
    if cmd == "disable":
        from namel3ss.cli.packs_disable_mode import run_packs_disable

        return run_packs_disable(tail, json_mode=json_mode)
    if cmd == "keys":
        from namel3ss.cli.packs_keys_mode import run_packs_keys

        return run_packs_keys(tail, json_mode=json_mode)
    raise Namel3ssError(
        build_guidance_message(
            what=f"Unknown packs command '{cmd}'.",
            why="Supported commands are add, remove, status, verify, enable, disable, and keys.",
            fix="Run `n3 packs help` to see usage.",
            example="n3 packs status",
        )
    )


def _print_usage() -> None:
    usage = """Usage:
  n3 packs add <path_or_zip> [--json]
  n3 packs remove <pack_id> --yes [--json]
  n3 packs status [--json]
  n3 packs verify <pack_id> [--json]
  n3 packs enable <pack_id> [--json]
  n3 packs disable <pack_id> [--json]
  n3 packs keys add --id <id> --public-key <path> [--json]
"""
    print(usage.strip())


__all__ = ["run_packs"]
