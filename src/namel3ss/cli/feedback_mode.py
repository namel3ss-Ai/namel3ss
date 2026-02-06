from __future__ import annotations

from dataclasses import dataclass
import sys

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.feedback import load_feedback_entries


@dataclass(frozen=True)
class _FeedbackParams:
    app_arg: str | None
    json_mode: bool



def run_feedback_command(args: list[str]) -> int:
    try:
        if not args or args[0] in {"list", "help", "-h", "--help"}:
            tail = args
            if args and args[0] in {"list", "help", "-h", "--help"}:
                tail = args[1:]
            if args and args[0] in {"help", "-h", "--help"}:
                _print_usage()
                return 0
            params = _parse_list_args(tail)
            app_path = resolve_app_path(params.app_arg)
            entries = load_feedback_entries(app_path.parent, app_path)
            payload = {
                "ok": True,
                "count": len(entries),
                "entries": [entry.to_dict() for entry in entries],
            }
            if params.json_mode:
                print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
                return 0
            _print_human(entries)
            return 0
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unknown feedback command '{args[0]}'.",
                why="feedback supports list only in this phase.",
                fix="Use n3 feedback list.",
                example="n3 feedback list --json",
            )
        )
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1



def _parse_list_args(args: list[str]) -> _FeedbackParams:
    app_arg = None
    json_mode = False
    i = 0
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
                    why="feedback list supports --json only.",
                    fix="Remove the unsupported flag.",
                    example="n3 feedback list --json",
                )
            )
        if app_arg is None:
            app_arg = arg
            i += 1
            continue
        raise Namel3ssError(
            build_guidance_message(
                what="Too many positional arguments.",
                why="feedback list accepts at most one app path.",
                fix="Provide one app.ai path or none.",
                example="n3 feedback list app.ai",
            )
        )
    return _FeedbackParams(app_arg=app_arg, json_mode=json_mode)



def _print_human(entries) -> None:
    if not entries:
        print("No feedback entries yet.")
        return
    print("Feedback entries")
    for entry in entries:
        comment = f" comment={entry.comment}" if entry.comment else ""
        print(
            f"  step={entry.step_count} flow={entry.flow_name} input_id={entry.input_id} rating={entry.rating}{comment}"
        )



def _print_usage() -> None:
    print("Usage:\n  n3 feedback list [app.ai] [--json]")


__all__ = ["run_feedback_command"]
