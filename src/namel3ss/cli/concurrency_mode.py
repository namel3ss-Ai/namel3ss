from __future__ import annotations

from dataclasses import dataclass
import sys

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.concurrency import run_concurrency_checks
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error


@dataclass(frozen=True)
class _ConcurrencyParams:
    subcommand: str
    app_arg: str | None
    json_mode: bool


def run_concurrency_command(args: list[str]) -> int:
    try:
        params = _parse_args(args)
        if params.subcommand == "help":
            _print_usage()
            return 0
        app_path = resolve_app_path(params.app_arg)
        source = app_path.read_text(encoding="utf-8")
        payload = run_concurrency_checks(source)
        if params.json_mode:
            print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
            return 0 if bool(payload.get("ok")) else 1
        _print_human(payload)
        return 0 if bool(payload.get("ok")) else 1
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> _ConcurrencyParams:
    if not args:
        return _ConcurrencyParams(subcommand="check", app_arg=None, json_mode=False)
    subcommand = str(args[0] or "").strip().lower()
    if subcommand in {"help", "-h", "--help"}:
        return _ConcurrencyParams(subcommand="help", app_arg=None, json_mode=False)
    if subcommand != "check":
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
        raise Namel3ssError(_too_many_args_message())
    return _ConcurrencyParams(subcommand="check", app_arg=positional[0] if positional else None, json_mode=json_mode)


def _print_human(payload: dict[str, object]) -> None:
    print("Concurrency check")
    print(f"  ok: {bool(payload.get('ok'))}")
    print(f"  violations: {int(payload.get('count') or 0)}")
    violations = payload.get("violations")
    if isinstance(violations, list):
        for item in violations[:100]:
            if not isinstance(item, dict):
                continue
            print(
                f"  line {item.get('line')}:{item.get('column')} "
                f"{item.get('flow_name')} {item.get('reason')}"
            )


def _print_usage() -> None:
    print("Usage:\n  n3 concurrency check [app.ai] [--json]")


def _unknown_subcommand_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"Unknown concurrency command '{subcommand}'.",
        why="Only `check` is supported.",
        fix="Use `n3 concurrency check`.",
        example="n3 concurrency check --json",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="concurrency check supports only --json.",
        fix="Remove unsupported flags.",
        example="n3 concurrency check --json",
    )


def _too_many_args_message() -> str:
    return build_guidance_message(
        what="Too many positional arguments.",
        why="concurrency check takes at most one optional app path.",
        fix="Pass only one app.ai path.",
        example="n3 concurrency check app.ai",
    )


__all__ = ["run_concurrency_command"]
