from __future__ import annotations

import sys

from namel3ss.cli.app_path import default_missing_app_message, resolve_app_path
from namel3ss.cli.devex import parse_project_overrides
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.module_loader import load_project
from namel3ss.theme import resolve_theme_definition, resolve_token_registry


def run_validate_command(args: list[str]) -> int:
    try:
        if not args or args[0] in {"help", "-h", "--help"}:
            _print_usage()
            return 0
        subcommand = args[0]
        if subcommand != "theme":
            raise Namel3ssError(_unknown_subcommand_message(subcommand))
        return _run_validate_theme(args[1:])
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _run_validate_theme(args: list[str]) -> int:
    overrides, remaining = parse_project_overrides(args)
    json_mode, app_arg = _parse_theme_args(remaining)
    app_path = resolve_app_path(
        app_arg or overrides.app_path,
        project_root=overrides.project_root,
        search_parents=False,
        missing_message=default_missing_app_message("validate theme"),
    )
    project = load_project(app_path)
    program = project.program
    capabilities = getattr(program, "capabilities", ()) or ()
    theme_definition = getattr(program, "theme_definition", None)
    resolved = resolve_theme_definition(theme_definition, capabilities=capabilities)
    token_registry = resolve_token_registry(
        resolved,
        legacy_tokens=getattr(program, "theme_tokens", {}) or {},
    )
    payload = {
        "ok": True,
        "app_path": app_path.as_posix(),
        "theme": {
            "preset": resolved.definition.preset,
            "harmonize": resolved.definition.harmonize,
            "allow_low_contrast": resolved.definition.allow_low_contrast,
            "brand_palette_size": len(resolved.definition.brand_palette),
            "token_count": len(token_registry),
        },
    }
    if json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0
    theme = payload["theme"]
    print("Theme validation succeeded.")
    print(f"preset: {theme['preset'] or 'none'}")
    print(f"harmonize: {str(theme['harmonize']).lower()}")
    print(f"allow_low_contrast: {str(theme['allow_low_contrast']).lower()}")
    print(f"brand_palette_size: {theme['brand_palette_size']}")
    print(f"token_count: {theme['token_count']}")
    return 0


def _parse_theme_args(args: list[str]) -> tuple[bool, str | None]:
    json_mode = False
    app_arg: str | None = None
    for arg in args:
        if arg == "--json":
            json_mode = True
            continue
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg))
        if app_arg is None:
            app_arg = arg
            continue
        raise Namel3ssError(
            build_guidance_message(
                what="validate theme accepts at most one app path.",
                why="Too many positional arguments were provided.",
                fix="Provide a single app path or rely on default app.ai.",
                example="n3 validate theme app.ai",
            )
        )
    return json_mode, app_arg


def _unknown_subcommand_message(value: str) -> str:
    return build_guidance_message(
        what=f"Unknown validate command '{value}'.",
        why="validate currently supports theme only.",
        fix="Run n3 validate theme <app.ai>.",
        example="n3 validate theme app.ai",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="validate theme supports --json only.",
        fix="Remove unsupported flags.",
        example="n3 validate theme app.ai --json",
    )


def _print_usage() -> None:
    usage = """Usage:
  n3 validate theme [app.ai] [--json]
"""
    print(usage.strip())


__all__ = ["run_validate_command"]
