from __future__ import annotations

from dataclasses import dataclass
import sys

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.quality import run_quality_checks, suggest_quality_fixes


@dataclass(frozen=True)
class _QualityParams:
    subcommand: str
    app_arg: str | None
    json_mode: bool


def run_quality_command(args: list[str]) -> int:
    try:
        params = _parse_args(args)
        if params.subcommand == "help":
            _print_usage()
            return 0

        app_path = resolve_app_path(params.app_arg)
        source = app_path.read_text(encoding="utf-8")
        report = run_quality_checks(source, project_root=app_path.parent, app_path=app_path)

        if params.subcommand == "fix":
            report = dict(report)
            report["fixes"] = suggest_quality_fixes(report)

        if params.json_mode:
            print(canonical_json_dumps(report, pretty=True, drop_run_keys=False))
            return 0

        _print_human(report, include_fixes=params.subcommand == "fix")
        return 0 if bool(report.get("ok")) else 1
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> _QualityParams:
    if not args:
        return _QualityParams(subcommand="check", app_arg=None, json_mode=False)
    subcommand = args[0].strip().lower()
    if subcommand in {"help", "-h", "--help"}:
        return _QualityParams(subcommand="help", app_arg=None, json_mode=False)
    if subcommand not in {"check", "fix"}:
        raise Namel3ssError(_unknown_subcommand_message(subcommand))

    json_mode = False
    positional: list[str] = []
    for arg in args[1:]:
        if arg == "--json":
            json_mode = True
            continue
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg))
        positional.append(arg)
    if len(positional) > 1:
        raise Namel3ssError(_too_many_args_message(subcommand))
    return _QualityParams(subcommand=subcommand, app_arg=positional[0] if positional else None, json_mode=json_mode)


def _print_human(report: dict[str, object], *, include_fixes: bool) -> None:
    ok = bool(report.get("ok"))
    count = int(report.get("count") or 0)
    print("Quality check")
    print(f"  ok: {ok}")
    print(f"  issues: {count}")
    issues = report.get("issues")
    if isinstance(issues, list):
        for item in issues[:50]:
            if not isinstance(item, dict):
                continue
            print(
                f"  {item.get('code')} {item.get('entity')} "
                f"{item.get('issue')}"
            )
    if include_fixes:
        fixes = report.get("fixes")
        if isinstance(fixes, list):
            print(f"  fixes: {len(fixes)}")
            for fix in fixes:
                print(f"  - {fix}")


def _print_usage() -> None:
    print(
        "Usage:\n"
        "  n3 quality check [app.ai] [--json]\n"
        "  n3 quality fix [app.ai] [--json]"
    )


def _unknown_subcommand_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"Unknown quality command '{subcommand}'.",
        why="Supported commands are check and fix.",
        fix="Use quality check or quality fix.",
        example="n3 quality check --json",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="quality commands support only --json.",
        fix="Remove the unsupported flag.",
        example="n3 quality check --json",
    )


def _too_many_args_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"quality {subcommand} has too many positional arguments.",
        why="Only one optional app path is supported.",
        fix="Pass at most one app.ai path.",
        example=f"n3 quality {subcommand} app.ai",
    )


__all__ = ["run_quality_command"]
