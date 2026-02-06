from __future__ import annotations

from pathlib import Path
import sys

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.lsp import diagnostics_for_text, serve_stdio


def run_lsp_command(args: list[str]) -> int:
    try:
        params = _parse_args(args)
        if params["subcommand"] == "help":
            _print_usage()
            return 0
        if params["subcommand"] == "stdio":
            serve_stdio(sys.stdin.buffer, sys.stdout.buffer)
            return 0
        if params["subcommand"] == "check":
            app_path = resolve_app_path(params["app_arg"])
            diagnostics = diagnostics_for_text(Path(app_path).read_text(encoding="utf-8"))
            payload = {"ok": len(diagnostics) == 0, "count": len(diagnostics), "diagnostics": diagnostics}
            if bool(params["json_mode"]):
                print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
                return 0 if payload["ok"] else 1
            print(f"Diagnostics: {len(diagnostics)}")
            for diag in diagnostics:
                print(f"  - {diag.get('message')}")
            return 0 if payload["ok"] else 1
        raise Namel3ssError(_unknown_subcommand_message(str(params["subcommand"])))
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> dict[str, object]:
    if not args or args[0] in {"help", "-h", "--help"}:
        return {"subcommand": "help", "json_mode": False, "app_arg": None}
    subcommand = args[0].strip().lower()
    if subcommand in {"stdio", "serve"}:
        if len(args) > 1:
            raise Namel3ssError(_usage_message())
        return {"subcommand": "stdio", "json_mode": False, "app_arg": None}
    if subcommand == "check":
        json_mode = "--json" in args[1:]
        positional = [item for item in args[1:] if item != "--json"]
        if len(positional) > 1:
            raise Namel3ssError(_usage_message())
        return {"subcommand": "check", "json_mode": json_mode, "app_arg": positional[0] if positional else None}
    raise Namel3ssError(_unknown_subcommand_message(subcommand))


def _print_usage() -> None:
    print(
        "Usage:\n"
        "  n3 lsp stdio\n"
        "  n3 lsp check [app.ai] [--json]"
    )


def _usage_message() -> str:
    return build_guidance_message(
        what="Invalid lsp arguments.",
        why="lsp supports 'stdio' or 'check [app.ai] [--json]'.",
        fix="Use one of the documented forms.",
        example="n3 lsp check app.ai --json",
    )


def _unknown_subcommand_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"Unknown lsp command '{subcommand}'.",
        why="Supported commands are stdio and check.",
        fix="Run n3 lsp help.",
        example="n3 lsp stdio",
    )


__all__ = ["run_lsp_command"]
