from __future__ import annotations

from dataclasses import dataclass
import sys

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.args import allow_aliases_from_flags
from namel3ss.cli.devex import parse_project_overrides
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.module_loader import load_project
from namel3ss.typecheck import run_type_check


@dataclass(frozen=True)
class _TypeParams:
    subcommand: str
    app_arg: str | None
    json_mode: bool
    disabled: bool


def run_type_command(args: list[str]) -> int:
    try:
        overrides, remaining = parse_project_overrides(args)
        params = _parse_args(remaining)
        if params.subcommand == "help":
            _print_usage()
            return 0
        if params.disabled:
            payload = {"ok": True, "disabled": True, "count": 0, "issues": []}
            print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
            return 0
        if params.app_arg and overrides.app_path:
            raise Namel3ssError("App path was provided twice. Use either an explicit app path or --app.")
        app_path = resolve_app_path(
            params.app_arg or overrides.app_path,
            project_root=overrides.project_root,
        )
        project = load_project(app_path, allow_legacy_type_aliases=allow_aliases_from_flags(args))
        report = run_type_check(project.app_ast)
        report["path"] = app_path.as_posix()
        print(canonical_json_dumps(report, pretty=True, drop_run_keys=False))
        return 0 if bool(report.get("ok")) else 1
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> _TypeParams:
    if not args:
        return _TypeParams(subcommand="check", app_arg=None, json_mode=True, disabled=False)
    subcommand = str(args[0]).strip().lower()
    if subcommand in {"help", "-h", "--help"}:
        return _TypeParams(subcommand="help", app_arg=None, json_mode=False, disabled=False)
    if subcommand != "check":
        raise Namel3ssError(_unknown_subcommand_message(subcommand))
    app_arg = None
    disabled = False
    for token in args[1:]:
        if token == "--json":
            continue
        if token == "--disable-types":
            disabled = True
            continue
        if token.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(token))
        if app_arg is None:
            app_arg = token
            continue
        raise Namel3ssError(_too_many_args_message())
    return _TypeParams(subcommand="check", app_arg=app_arg, json_mode=True, disabled=disabled)


def _print_usage() -> None:
    print(
        "Usage:\n"
        "  n3 type check [app.ai] [--json] [--disable-types]\n"
        "  n3 type help"
    )


def _unknown_subcommand_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"Unknown type command '{subcommand}'.",
        why="Supported subcommands are check and help.",
        fix="Use n3 type check.",
        example="n3 type check app.ai --json",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="type check supports --json and --disable-types.",
        fix="Remove the unsupported flag.",
        example="n3 type check --disable-types",
    )


def _too_many_args_message() -> str:
    return build_guidance_message(
        what="type check accepts one optional app path.",
        why="Extra positional arguments are not used.",
        fix="Pass only app.ai or no positional argument.",
        example="n3 type check app.ai",
    )


__all__ = ["run_type_command"]
