from __future__ import annotations

from dataclasses import dataclass
import sys

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.observability.config import init_observability_config


@dataclass(frozen=True)
class _Params:
    subcommand: str
    app_arg: str | None
    json_mode: bool
    overwrite: bool


def run_observability_command(args: list[str]) -> int:
    try:
        params = _parse_args(args)
        if params.subcommand == "help":
            _print_usage()
            return 0
        if params.subcommand != "init":
            raise Namel3ssError(_unknown_subcommand_message(params.subcommand))
        app_path = resolve_app_path(params.app_arg)
        path = init_observability_config(
            project_root=app_path.parent,
            app_path=app_path,
            overwrite=params.overwrite,
        )
        payload = {"ok": True, "config_path": path.as_posix(), "overwrite": params.overwrite}
        return _emit(payload, json_mode=params.json_mode)
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> _Params:
    if not args or args[0] in {"help", "-h", "--help"}:
        return _Params(subcommand="help", app_arg=None, json_mode=False, overwrite=False)
    subcommand = args[0].strip().lower()
    json_mode = False
    overwrite = False
    positional: list[str] = []
    i = 1
    while i < len(args):
        arg = args[i]
        if arg == "--json":
            json_mode = True
            i += 1
            continue
        if arg == "--overwrite":
            overwrite = True
            i += 1
            continue
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg))
        positional.append(arg)
        i += 1
    if len(positional) > 1:
        raise Namel3ssError(_too_many_args_message(subcommand))
    app_arg = positional[0] if positional else None
    return _Params(subcommand=subcommand, app_arg=app_arg, json_mode=json_mode, overwrite=overwrite)


def _emit(payload: dict[str, object], *, json_mode: bool) -> int:
    if json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0 if bool(payload.get("ok")) else 1
    print("Observability")
    print(f"  ok: {payload.get('ok')}")
    print(f"  config_path: {payload.get('config_path')}")
    print(f"  overwrite: {payload.get('overwrite')}")
    return 0 if bool(payload.get("ok")) else 1


def _print_usage() -> None:
    print(
        "Usage:\n"
        "  n3 observability init [app.ai] [--overwrite] [--json]"
    )


def _unknown_subcommand_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"Unknown observability command '{subcommand}'.",
        why="Supported command is init.",
        fix="Use n3 observability init.",
        example="n3 observability init",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="observability init supports --overwrite and --json.",
        fix="Remove the unsupported flag.",
        example="n3 observability init --json",
    )


def _too_many_args_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"observability {subcommand} has too many positional arguments.",
        why="Only one optional app path is supported.",
        fix="Remove extra positional values.",
        example=f"n3 observability {subcommand}",
    )


__all__ = ["run_observability_command"]
