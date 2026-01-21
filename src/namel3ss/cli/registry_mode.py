from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def run_registry(args: list[str]) -> int:
    if not args or args[0] in {"help", "-h", "--help"}:
        _print_usage()
        return 0
    cmd = args[0]
    tail = args[1:]
    json_mode = "--json" in tail
    tail = [item for item in tail if item != "--json"]
    if cmd == "add":
        from namel3ss.cli.registry_add_mode import run_registry_add

        return run_registry_add(tail, json_mode=json_mode)
    if cmd == "list":
        from namel3ss.cli.registry_list_mode import run_registry_list

        return run_registry_list(tail, json_mode=json_mode)
    if cmd == "search":
        from namel3ss.cli.registry_search_mode import run_registry_search

        return run_registry_search(tail, json_mode=json_mode)
    if cmd == "info":
        from namel3ss.cli.registry_info_mode import run_registry_info

        return run_registry_info(tail, json_mode=json_mode)
    if cmd == "build":
        from namel3ss.cli.registry_build_mode import run_registry_build

        return run_registry_build(tail, json_mode=json_mode)
    raise Namel3ssError(
        build_guidance_message(
            what=f"Unknown registry command '{cmd}'.",
            why="Supported commands are add, build, list, search, and info.",
            fix="Run `n3 registry help` to see usage.",
            example="n3 registry build",
        )
    )


def _print_usage() -> None:
    usage = """Usage:
  n3 registry add bundle_path --json
  n3 registry build --json
  n3 registry list --registry alias_or_url --offline --json
  n3 registry search phrase --capability network|filesystem|secrets|subprocess|env --risk low|medium|high --json
  n3 registry info pack_id --registry alias_or_url --offline --json
  Notes:
    flags are optional unless stated
"""
    print(usage.strip())


__all__ = ["run_registry"]
