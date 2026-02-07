from __future__ import annotations

import sys
from pathlib import Path

from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.plugin.ui_scaffold import scaffold_ui_plugin
from namel3ss.ui_pack.scaffold import scaffold_ui_pack


def run_create_command(args: list[str]) -> int:
    try:
        if not args or args[0] in {"help", "-h", "--help"}:
            _print_usage()
            return 0
        json_mode, dry_run, positional = _parse_flags(args)
        if not positional:
            raise Namel3ssError(_missing_kind_message())
        kind = positional[0]
        if kind == "plugin":
            if len(positional) != 2:
                raise Namel3ssError(_plugin_usage_message())
            result = scaffold_ui_plugin(positional[1], Path.cwd(), dry_run=dry_run)
            payload = {
                "ok": True,
                "kind": "plugin",
                "name": result.target.name,
                "path": result.target.as_posix(),
                "dry_run": result.dry_run,
                "files": list(result.files),
            }
            return _emit(payload, json_mode=json_mode)
        if kind in {"ui_pack", "ui-pack"}:
            if len(positional) != 2:
                raise Namel3ssError(_ui_pack_usage_message())
            result = scaffold_ui_pack(positional[1], Path.cwd(), dry_run=dry_run)
            payload = {
                "ok": True,
                "kind": "ui_pack",
                "name": result.target.name,
                "path": result.target.as_posix(),
                "dry_run": result.dry_run,
                "files": list(result.files),
            }
            return _emit(payload, json_mode=json_mode)
        raise Namel3ssError(_unknown_kind_message(kind))
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_flags(args: list[str]) -> tuple[bool, bool, list[str]]:
    json_mode = False
    dry_run = False
    positional: list[str] = []
    for arg in args:
        if arg == "--json":
            json_mode = True
            continue
        if arg == "--dry-run":
            dry_run = True
            continue
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg))
        positional.append(arg)
    return json_mode, dry_run, positional


def _emit(payload: dict[str, object], *, json_mode: bool) -> int:
    if json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0
    print(f"Created {payload['kind']}: {payload['path']}")
    if payload.get("dry_run"):
        print("Dry run only. No files were written.")
    files = payload.get("files")
    if isinstance(files, list) and files:
        print("Files")
        for rel in files:
            print(f"  - {rel}")
    return 0


def _missing_kind_message() -> str:
    return build_guidance_message(
        what="create requires a target kind.",
        why="Supported kinds are plugin and ui_pack.",
        fix="Use n3 create plugin <name> or n3 create ui_pack <name>.",
        example="n3 create plugin charts",
    )


def _plugin_usage_message() -> str:
    return build_guidance_message(
        what="create plugin requires exactly one name.",
        why="The plugin scaffold command accepts a single name argument.",
        fix="Pass one plugin name.",
        example="n3 create plugin maps",
    )


def _ui_pack_usage_message() -> str:
    return build_guidance_message(
        what="create ui_pack requires exactly one name.",
        why="The ui_pack scaffold command accepts a single name argument.",
        fix="Pass one ui_pack name.",
        example="n3 create ui_pack enterprise_dashboard",
    )


def _unknown_kind_message(kind: str) -> str:
    return build_guidance_message(
        what=f"Unknown create target '{kind}'.",
        why="Supported targets are plugin and ui_pack.",
        fix="Use one of the supported create targets.",
        example="n3 create plugin charts",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="create supports --dry-run and --json only.",
        fix="Remove unsupported flags.",
        example="n3 create plugin charts --dry-run",
    )


def _print_usage() -> None:
    usage = """Usage:
  n3 create plugin <name> [--dry-run] [--json]
  n3 create ui_pack <name> [--dry-run] [--json]
"""
    print(usage.strip())


__all__ = ["run_create_command"]
