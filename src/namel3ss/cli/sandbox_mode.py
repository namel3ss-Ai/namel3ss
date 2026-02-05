from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.sandbox.config import load_sandbox_config
from namel3ss.runtime.sandbox.runner import build_sandbox_image, run_sandbox_flow


def run_sandbox_command(args: list[str]) -> int:
    app_arg, remaining = _split_app_arg(args)
    cmd = remaining[0] if remaining else "list"
    tail = remaining[1:] if remaining else []
    if cmd == "list":
        return _list_sandboxes(app_arg, tail)
    if cmd == "build":
        return _build_sandbox(app_arg, tail)
    if cmd == "run":
        return _run_sandbox(app_arg, tail)
    raise Namel3ssError(f"Unknown sandbox subcommand '{cmd}'. Supported: list, build, run")


def _list_sandboxes(app_arg: str | None, args: list[str]) -> int:
    json_mode = "--json" in args
    if args and not json_mode:
        raise Namel3ssError("Usage: n3 sandbox list [--json]")
    app_path = resolve_app_path(app_arg)
    config = load_sandbox_config(app_path.parent, app_path)
    flows = sorted(config.flows.keys())
    if json_mode:
        payload = {
            "sandboxes": {
                name: {
                    "entry": flow.entry,
                    "command": flow.command,
                    "image": flow.image,
                    "cpu_seconds": flow.cpu_seconds,
                    "memory_mb": flow.memory_mb,
                    "timeout_seconds": flow.timeout_seconds,
                    "allow_network": flow.allow_network,
                }
                for name, flow in sorted(config.flows.items())
            }
        }
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0
    if not flows:
        print("No sandboxed flows configured.")
        return 0
    print("Sandboxed flows:")
    for name in flows:
        flow = config.flows[name]
        image = flow.image or "default"
        entry = flow.command or flow.entry or "unknown"
        print(f"- {name}: {entry} (image {image})")
    return 0


def _build_sandbox(app_arg: str | None, args: list[str]) -> int:
    flow_name = _require_flow_name(args, "build")
    app_path = resolve_app_path(app_arg)
    result = build_sandbox_image(
        project_root=app_path.parent,
        app_path=app_path,
        flow_name=flow_name,
    )
    print(result)
    return 0


def _run_sandbox(app_arg: str | None, args: list[str]) -> int:
    params = _parse_run_args(args)
    app_path = resolve_app_path(app_arg)
    payload = {}
    if params.input_path:
        input_path = Path(params.input_path)
        if not input_path.exists():
            raise Namel3ssError(_missing_input_message(params.input_path))
        try:
            payload = json.loads(input_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as err:
            raise Namel3ssError(_invalid_input_message(params.input_path, err)) from err
    result = run_sandbox_flow(
        project_root=app_path.parent,
        app_path=app_path,
        flow_name=params.flow_name,
        payload=payload,
    )
    print(canonical_json_dumps(result, pretty=True, drop_run_keys=False))
    return 0


class _RunParams:
    def __init__(self, flow_name: str, input_path: str | None) -> None:
        self.flow_name = flow_name
        self.input_path = input_path


def _parse_run_args(args: list[str]) -> _RunParams:
    flow_name = None
    input_path = None
    idx = 0
    while idx < len(args):
        arg = args[idx]
        if arg == "--input":
            if idx + 1 >= len(args):
                raise Namel3ssError(_missing_flag_value("--input"))
            input_path = args[idx + 1]
            idx += 2
            continue
        if arg.startswith("-"):
            raise Namel3ssError(_unknown_flag_message(arg))
        if flow_name is None:
            flow_name = arg
            idx += 1
            continue
        raise Namel3ssError(_too_many_args_message("run"))
    if not flow_name:
        raise Namel3ssError(_missing_flow_name_message("run"))
    return _RunParams(flow_name=flow_name, input_path=input_path)


def _split_app_arg(args: list[str]) -> tuple[str | None, list[str]]:
    if args and args[0].endswith(".ai"):
        return args[0], args[1:]
    return None, args


def _require_flow_name(args: list[str], command: str) -> str:
    if not args or args[0].startswith("-"):
        raise Namel3ssError(_missing_flow_name_message(command))
    if len(args) > 1:
        raise Namel3ssError(_too_many_args_message(command))
    return args[0]


def _missing_flow_name_message(command: str) -> str:
    return build_guidance_message(
        what=f"Sandbox {command} requires a flow name.",
        why="No flow name was provided.",
        fix="Provide a flow name after the command.",
        example=f"n3 sandbox {command} summarize",
    )


def _too_many_args_message(command: str) -> str:
    return build_guidance_message(
        what=f"Too many arguments for sandbox {command}.",
        why="Sandbox commands accept a single flow name.",
        fix="Remove extra arguments.",
        example=f"n3 sandbox {command} summarize",
    )


def _missing_flag_value(flag: str) -> str:
    return build_guidance_message(
        what=f"{flag} flag is missing a value.",
        why="An input file path is required.",
        fix=f"Provide a path after {flag}.",
        example=f"{flag} input.json",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="Supported flags: --input.",
        fix="Remove the unsupported flag.",
        example="n3 sandbox run summarize --input input.json",
    )


def _missing_input_message(path: str) -> str:
    return build_guidance_message(
        what=f"Input file not found: {path}.",
        why="The path does not exist.",
        fix="Check the file name and try again.",
        example="n3 sandbox run summarize --input input.json",
    )


def _invalid_input_message(path: str, err: json.JSONDecodeError) -> str:
    where = f" at line {err.lineno}, column {err.colno}" if err.lineno and err.colno else ""
    return build_guidance_message(
        what=f"Input file is not valid JSON: {path}.",
        why=f"JSON parsing failed{where}: {err.msg}.",
        fix="Provide valid JSON input.",
        example="n3 sandbox run summarize --input input.json",
    )


__all__ = ["run_sandbox_command"]
