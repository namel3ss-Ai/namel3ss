from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.plugin.scaffold import scaffold_plugin


def run_plugin_command(args: list[str]) -> int:
    if not args or args[0] in {"help", "-h", "--help"}:
        _print_usage()
        return 0
    cmd = args[0]
    tail = args[1:]
    if cmd == "new":
        return _run_new(tail)
    raise Namel3ssError(
        build_guidance_message(
            what=f"Unknown plugin command '{cmd}'.",
            why="Supported commands are new.",
            fix="Use n3 plugin new.",
            example="n3 plugin new node demo_plugin",
        )
    )


def _run_new(args: list[str]) -> int:
    if len(args) < 2:
        raise Namel3ssError(_missing_args_message())
    if len(args) > 2:
        raise Namel3ssError(_too_many_args_message(args[2:]))
    language = args[0]
    name = args[1]
    target = scaffold_plugin(language, name, Path.cwd())
    print(f"Created plugin at {target}")
    print("Next step")
    print(f"  cd {target.name}")
    return 0


def _missing_args_message() -> str:
    return build_guidance_message(
        what="Plugin scaffolding requires a language and name.",
        why="No language or name was provided.",
        fix="Provide a language and plugin name.",
        example="n3 plugin new node demo_plugin",
    )


def _too_many_args_message(args: list[str]) -> str:
    extra = " ".join(args)
    return build_guidance_message(
        what=f"Too many arguments: {extra}.",
        why="Plugin scaffolding accepts a language and name.",
        fix="Remove the extra arguments.",
        example="n3 plugin new go demo_plugin",
    )


def _print_usage() -> None:
    usage = """Usage:
  n3 plugin new <language> <name>

Examples:
  n3 plugin new node demo_plugin
  n3 plugin new go demo_plugin
  n3 plugin new rust demo_plugin
"""
    print(usage.strip())


__all__ = ["run_plugin_command"]
