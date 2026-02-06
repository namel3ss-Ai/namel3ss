from __future__ import annotations

from dataclasses import dataclass
import sys

from namel3ss.cir import build_cir, cir_to_payload
from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.args import allow_aliases_from_flags
from namel3ss.cli.devex import parse_project_overrides
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.module_loader import load_project


@dataclass(frozen=True)
class _AstParams:
    subcommand: str
    app_arg: str | None
    json_mode: bool


def run_ast_command(args: list[str]) -> int:
    try:
        overrides, remaining = parse_project_overrides(args)
        params = _parse_args(remaining)
        if params.subcommand == "help":
            _print_usage()
            return 0
        if params.app_arg and overrides.app_path:
            raise Namel3ssError("App path was provided twice. Use either an explicit app path or --app.")
        app_path = resolve_app_path(
            params.app_arg or overrides.app_path,
            project_root=overrides.project_root,
        )
        allow_aliases = allow_aliases_from_flags(args)
        project = load_project(app_path, allow_legacy_type_aliases=allow_aliases)
        cir = build_cir(project.app_ast)
        payload = {
            "ok": True,
            "path": app_path.as_posix(),
            "schema": "cir.v1",
            "ast": cir_to_payload(cir),
        }
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> _AstParams:
    if not args:
        return _AstParams(subcommand="dump", app_arg=None, json_mode=True)
    subcommand = str(args[0]).strip().lower()
    if subcommand in {"help", "-h", "--help"}:
        return _AstParams(subcommand="help", app_arg=None, json_mode=False)
    if subcommand != "dump":
        raise Namel3ssError(_unknown_subcommand_message(subcommand))
    json_mode = True
    positional: list[str] = []
    for token in args[1:]:
        if token == "--json":
            json_mode = True
            continue
        if token.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(token))
        positional.append(token)
    if len(positional) > 1:
        raise Namel3ssError(_too_many_args_message())
    return _AstParams(subcommand="dump", app_arg=positional[0] if positional else None, json_mode=json_mode)


def _print_usage() -> None:
    print(
        "Usage:\n"
        "  n3 ast dump [app.ai] [--json]\n"
        "  n3 ast help"
    )


def _unknown_subcommand_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"Unknown ast command '{subcommand}'.",
        why="Supported ast subcommands are dump and help.",
        fix="Use n3 ast dump.",
        example="n3 ast dump app.ai --json",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="ast supports only --json.",
        fix="Remove the unsupported flag.",
        example="n3 ast dump --json",
    )


def _too_many_args_message() -> str:
    return build_guidance_message(
        what="ast dump accepts one optional app path.",
        why="Extra positional arguments are not used.",
        fix="Pass only app.ai or no positional argument.",
        example="n3 ast dump app.ai",
    )


__all__ = ["run_ast_command"]
