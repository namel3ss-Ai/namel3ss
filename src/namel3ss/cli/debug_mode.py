from __future__ import annotations

from dataclasses import dataclass
import sys

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.runtime.debugger import Debugger


@dataclass(frozen=True)
class _DebugParams:
    action: str
    run_id: str | None
    app_arg: str | None
    json_mode: bool


def run_debug_command(args: list[str]) -> int:
    try:
        params = _parse_args(args)
        if params.action == "help":
            _print_usage()
            return 0
        app_path = resolve_app_path(params.app_arg)
        debugger = Debugger(project_root=app_path.parent, app_path=app_path)
        run_id = str(params.run_id or "").strip()
        if params.action == "pause":
            payload = debugger.pause(run_id)
        elif params.action == "step":
            payload = debugger.step(run_id)
        elif params.action == "back":
            payload = debugger.back(run_id)
        elif params.action == "replay":
            payload = debugger.replay(run_id)
        elif params.action == "show":
            payload = debugger.show(run_id)
        else:
            raise Namel3ssError(_unknown_action_message(params.action))
        return _emit(payload, json_mode=params.json_mode)
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> _DebugParams:
    if not args or args[0] in {"help", "-h", "--help"}:
        return _DebugParams(action="help", run_id=None, app_arg=None, json_mode=False)
    action = args[0].strip().lower()
    json_mode = False
    positional: list[str] = []
    i = 1
    while i < len(args):
        arg = args[i]
        if arg == "--json":
            json_mode = True
            i += 1
            continue
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg))
        positional.append(arg)
        i += 1
    if action not in {"pause", "step", "back", "replay", "show"}:
        raise Namel3ssError(_unknown_action_message(action))
    if not positional:
        raise Namel3ssError(_missing_run_id_message())
    if len(positional) > 2:
        raise Namel3ssError(_too_many_args_message(action))
    run_id = positional[0]
    app_arg = positional[1] if len(positional) == 2 else None
    return _DebugParams(action=action, run_id=run_id, app_arg=app_arg, json_mode=json_mode)


def _emit(payload: dict[str, object], *, json_mode: bool) -> int:
    if json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0 if bool(payload.get("ok")) else 1
    print("Debug")
    print(f"  ok: {payload.get('ok')}")
    print(f"  run_id: {payload.get('run_id')}")
    print(f"  paused: {payload.get('paused')}")
    print(f"  current_step: {payload.get('current_step')} / {payload.get('total_steps')}")
    current_entry = payload.get("current_entry")
    if isinstance(current_entry, dict):
        print(f"  step: {current_entry.get('step_id')} ({current_entry.get('step_name')})")
    state = payload.get("state")
    if isinstance(state, dict):
        print(f"  history_steps: {state.get('history_steps')}")
    return 0 if bool(payload.get("ok")) else 1


def _print_usage() -> None:
    print(
        "Usage:\n"
        "  n3 debug pause <run_id> [app.ai] [--json]\n"
        "  n3 debug step <run_id> [app.ai] [--json]\n"
        "  n3 debug back <run_id> [app.ai] [--json]\n"
        "  n3 debug replay <run_id> [app.ai] [--json]\n"
        "  n3 debug show <run_id> [app.ai] [--json]"
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="debug supports only --json.",
        fix="Remove the unsupported flag.",
        example="n3 debug replay demo-000001 --json",
    )


def _unknown_action_message(action: str) -> str:
    return build_guidance_message(
        what=f"Unknown debug action '{action}'.",
        why="Supported actions are pause, step, back, replay, and show.",
        fix="Use a supported debug action.",
        example="n3 debug replay demo-000001",
    )


def _missing_run_id_message() -> str:
    return build_guidance_message(
        what="Debug run id is missing.",
        why="debug commands require a run id.",
        fix="Use n3 trace list and pass one run id.",
        example="n3 debug show demo-000001",
    )


def _too_many_args_message(action: str) -> str:
    return build_guidance_message(
        what=f"debug {action} has too many positional arguments.",
        why="Only one optional app path is supported.",
        fix="Remove extra positional values.",
        example=f"n3 debug {action} demo-000001",
    )


__all__ = ["run_debug_command"]
