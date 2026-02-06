from __future__ import annotations

from pathlib import Path
import sys

from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.tutorials import list_tutorials, load_tutorial_progress, run_tutorial


def run_tutorial_command(args: list[str]) -> int:
    try:
        params = _parse_args(args)
        if params["subcommand"] == "help":
            _print_usage()
            return 0
        project_root = Path.cwd()
        if params["subcommand"] == "list":
            items = list_tutorials()
            progress = load_tutorial_progress(project_root)
            merged: list[dict[str, object]] = []
            for item in items:
                slug = str(item.get("slug") or "")
                status = progress.get(slug) or {}
                payload = dict(item)
                payload["completed"] = bool(status.get("completed", False))
                payload["last_passed"] = int(status.get("last_passed", 0))
                merged.append(payload)
            response = {"ok": True, "count": len(merged), "items": merged}
            return _emit(response, json_mode=bool(params["json_mode"]))
        if params["subcommand"] == "run":
            slug = str(params["slug"])
            response = run_tutorial(
                slug,
                project_root=project_root,
                answers=params["answers"],
                auto=bool(params["auto_mode"]),
            )
            return _emit(response, json_mode=bool(params["json_mode"]))
        raise Namel3ssError(_unknown_command_message(str(params["subcommand"])))
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> dict[str, object]:
    if not args or args[0] in {"help", "-h", "--help"}:
        return {"subcommand": "help", "json_mode": False, "slug": None, "answers": [], "auto_mode": False}
    subcommand = args[0].strip().lower()
    json_mode = False
    auto_mode = False
    answers: list[str] = []
    positional: list[str] = []

    i = 1
    while i < len(args):
        token = args[i]
        if token == "--json":
            json_mode = True
            i += 1
            continue
        if token == "--auto":
            auto_mode = True
            i += 1
            continue
        if token == "--answer":
            if i + 1 >= len(args):
                raise Namel3ssError(_missing_option_value_message(token))
            answers.append(args[i + 1])
            i += 2
            continue
        if token.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(token))
        positional.append(token)
        i += 1

    if subcommand == "list":
        if positional:
            raise Namel3ssError(_too_many_args_message(subcommand))
        return {
            "subcommand": subcommand,
            "json_mode": json_mode,
            "slug": None,
            "answers": answers,
            "auto_mode": auto_mode,
        }

    if subcommand == "run":
        if not positional:
            raise Namel3ssError(_missing_slug_message())
        if len(positional) > 1:
            raise Namel3ssError(_too_many_args_message(subcommand))
        return {
            "subcommand": subcommand,
            "json_mode": json_mode,
            "slug": positional[0],
            "answers": answers,
            "auto_mode": auto_mode,
        }

    raise Namel3ssError(_unknown_command_message(subcommand))


def _emit(payload: dict[str, object], *, json_mode: bool) -> int:
    if json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0 if bool(payload.get("ok")) else 1
    if "items" in payload:
        print("Tutorials")
        for item in payload.get("items", []):
            if not isinstance(item, dict):
                continue
            state = "done" if bool(item.get("completed", False)) else "todo"
            print(f"  {item.get('slug')} ({state}) - {item.get('title')}")
        return 0
    print(f"Tutorial {payload.get('slug')}")
    print(f"  completed: {payload.get('completed')}")
    print(f"  passed_steps: {payload.get('passed_steps')}/{payload.get('step_count')}")
    return 0


def _print_usage() -> None:
    print(
        "Usage:\n"
        "  n3 tutorial list [--json]\n"
        "  n3 tutorial run <slug> [--auto] [--answer TEXT ...] [--json]"
    )


def _unknown_command_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"Unknown tutorial command '{subcommand}'.",
        why="Supported tutorial commands are list and run.",
        fix="Run n3 tutorial help.",
        example="n3 tutorial list",
    )


def _too_many_args_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"Too many arguments for tutorial {subcommand}.",
        why="This command takes fewer positional values.",
        fix="Remove extra arguments.",
        example=f"n3 tutorial {subcommand}",
    )


def _missing_slug_message() -> str:
    return build_guidance_message(
        what="Tutorial slug is missing.",
        why="n3 tutorial run needs a lesson slug.",
        fix="Pick a slug from n3 tutorial list.",
        example="n3 tutorial run basics",
    )


def _missing_option_value_message(flag: str) -> str:
    return build_guidance_message(
        what=f"{flag} needs a value.",
        why="The command cannot parse options without values.",
        fix="Provide a value after the flag.",
        example="n3 tutorial run basics --answer ok",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="Supported flags are --json, --auto, and --answer.",
        fix="Remove the unsupported flag.",
        example="n3 tutorial list --json",
    )


__all__ = ["run_tutorial_command"]
