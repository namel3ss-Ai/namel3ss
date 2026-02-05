from __future__ import annotations

from dataclasses import dataclass
import sys

from namel3ss.cli.app_loader import load_program
from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.docs.prompts import collect_prompts
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error


@dataclass(frozen=True)
class _PromptsParams:
    subcommand: str
    app_arg: str | None
    json_mode: bool


def run_prompts_command(args: list[str]) -> int:
    try:
        params = _parse_args(args)
        if params.subcommand != "list":
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unknown prompts command '{params.subcommand}'.",
                    why="prompts supports list only.",
                    fix="Use n3 prompts list.",
                    example="n3 prompts list",
                )
            )
        app_path = resolve_app_path(params.app_arg)
        program, _ = load_program(app_path.as_posix())
        prompts = collect_prompts(program)
        payload = {"prompts": prompts}
        if params.json_mode:
            print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
            return 0
        _print_human(prompts)
        return 0
    except Namel3ssError as err:
        message = format_error(err, None)
        print(prepare_cli_text(message), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> _PromptsParams:
    if not args:
        raise Namel3ssError(
            build_guidance_message(
                what="Missing prompts subcommand.",
                why="prompts requires list.",
                fix="Add a subcommand.",
                example="n3 prompts list",
            )
        )
    subcommand = args[0]
    app_arg = None
    json_mode = False
    i = 1
    while i < len(args):
        arg = args[i]
        if arg == "--json":
            json_mode = True
            i += 1
            continue
        if arg.startswith("--"):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unknown flag '{arg}'.",
                    why="prompts supports --json only.",
                    fix="Remove the unsupported flag.",
                    example="n3 prompts list --json",
                )
            )
        if app_arg is None:
            app_arg = arg
            i += 1
            continue
        raise Namel3ssError(
            build_guidance_message(
                what="Too many positional arguments.",
                why="prompts accepts at most one app path.",
                fix="Provide a single app.ai path or none.",
                example="n3 prompts list app.ai",
            )
        )
    return _PromptsParams(subcommand=subcommand, app_arg=app_arg, json_mode=json_mode)


def _print_human(prompts: list[dict]) -> None:
    if not prompts:
        print("No prompts found.")
        return
    for prompt in prompts:
        name = prompt.get("name")
        version = prompt.get("version")
        description = prompt.get("description") or ""
        line = f"{name} {version}".strip()
        if description:
            line = f"{line} - {description}"
        print(line)


__all__ = ["run_prompts_command"]
