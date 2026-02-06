from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.args import allow_aliases_from_flags
from namel3ss.cli.devex import parse_project_overrides
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dump, canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.module_loader import load_project
from namel3ss.schema.inference import build_schema_migration_plan, infer_schema


@dataclass(frozen=True)
class _SchemaParams:
    subcommand: str
    app_arg: str | None
    json_mode: bool


def run_schema_command(args: list[str]) -> int:
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
        project = load_project(app_path, allow_legacy_type_aliases=allow_aliases_from_flags(args))
        if params.subcommand == "infer":
            payload = infer_schema(project.app_ast)
            output_path = _write_schema_artifact(app_path.parent, "schema_infer.json", payload)
            payload["output_path"] = output_path.as_posix()
        else:
            payload = build_schema_migration_plan(project.app_ast)
            output_path = _write_schema_artifact(app_path.parent, "schema_migrate.json", payload)
            payload["output_path"] = output_path.as_posix()
        payload["path"] = app_path.as_posix()
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> _SchemaParams:
    if not args:
        return _SchemaParams(subcommand="infer", app_arg=None, json_mode=True)
    subcommand = str(args[0]).strip().lower()
    if subcommand in {"help", "-h", "--help"}:
        return _SchemaParams(subcommand="help", app_arg=None, json_mode=False)
    if subcommand not in {"infer", "migrate"}:
        raise Namel3ssError(_unknown_subcommand_message(subcommand))
    app_arg = None
    for token in args[1:]:
        if token == "--json":
            continue
        if token.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(token))
        if app_arg is None:
            app_arg = token
            continue
        raise Namel3ssError(_too_many_args_message(subcommand))
    return _SchemaParams(subcommand=subcommand, app_arg=app_arg, json_mode=True)


def _write_schema_artifact(project_root: Path, filename: str, payload: dict[str, object]) -> Path:
    path = project_root / ".namel3ss" / filename
    canonical_json_dump(path, payload, pretty=True, drop_run_keys=False)
    return path


def _print_usage() -> None:
    print(
        "Usage:\n"
        "  n3 schema infer [app.ai] [--json]\n"
        "  n3 schema migrate [app.ai] [--json]\n"
        "  n3 schema help"
    )


def _unknown_subcommand_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"Unknown schema command '{subcommand}'.",
        why="Supported subcommands are infer, migrate, and help.",
        fix="Use n3 schema infer or n3 schema migrate.",
        example="n3 schema infer app.ai --json",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="schema commands support only --json.",
        fix="Remove the unsupported flag.",
        example="n3 schema migrate --json",
    )


def _too_many_args_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"schema {subcommand} accepts one optional app path.",
        why="Extra positional arguments are not used.",
        fix="Pass only app.ai or no positional argument.",
        example=f"n3 schema {subcommand} app.ai",
    )


__all__ = ["run_schema_command"]
