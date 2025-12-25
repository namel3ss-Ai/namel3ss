from __future__ import annotations

import json

from namel3ss.cli.app_loader import load_program
from namel3ss.cli.app_path import resolve_app_path
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.tools.bindings import load_tool_bindings, write_tool_bindings
from namel3ss.runtime.tools.bindings_yaml import ToolBinding
from namel3ss.runtime.tools.tool_pack_registry import is_tool_pack_tool
from namel3ss.utils.json_tools import dumps_pretty
from namel3ss.utils.slugify import slugify_tool_name


def run_tools_set_runner(args: list[str], *, json_mode: bool) -> int:
    tool_name, runner, url, image, command, env = _parse_set_runner_args(args)
    app_path = resolve_app_path(None)
    program, _ = load_program(str(app_path))
    if tool_name not in program.tools:
        raise Namel3ssError(
            build_guidance_message(
                what=f'Tool "{tool_name}" is not declared.',
                why="Runner configuration can only be updated for declared tools.",
                fix="Add the tool declaration to app.ai first.",
                example=f'tool "{tool_name}":\n  implemented using python',
            )
        )
    tool_decl = program.tools[tool_name]
    if tool_decl.kind != "python":
        raise Namel3ssError(
            build_guidance_message(
                what=f'Tool "{tool_name}" is not a python tool.',
                why=f"Tool kind is '{tool_decl.kind}'.",
                fix="Configure runners only for python tools.",
                example=f'tool "{tool_name}":\n  implemented using python',
            )
        )
    if is_tool_pack_tool(tool_name):
        raise Namel3ssError(
            build_guidance_message(
                what=f'Tool "{tool_name}" is a built-in pack tool.',
                why="Built-in packs are already bound and cannot be overridden.",
                fix="Rename the tool or remove the custom binding attempt.",
                example="n3 tools status",
            )
        )
    app_root = app_path.parent
    bindings = load_tool_bindings(app_root)
    binding = bindings.get(tool_name)
    if binding is None:
        raise Namel3ssError(
            build_guidance_message(
                what=f'Tool "{tool_name}" is not bound.',
                why="Runner settings live in .namel3ss/tools.yaml.",
                fix="Bind the tool first, then set the runner.",
                example=f'n3 tools bind "{tool_name}" --entry "tools.{slugify_tool_name(tool_name)}:run"',
            )
        )
    updated = ToolBinding(
        kind=binding.kind,
        entry=binding.entry,
        runner=runner,
        url=_next_url(binding, runner, url),
        image=_next_image(binding, runner, image),
        command=_next_command(binding, runner, command),
        env=_next_env(binding, runner, env),
        purity=binding.purity,
        timeout_ms=binding.timeout_ms,
    )
    bindings[tool_name] = updated
    path = write_tool_bindings(app_root, bindings)
    payload = {
        "status": "ok",
        "tool_name": tool_name,
        "runner": runner,
        "bindings_path": str(path),
    }
    if json_mode:
        print(dumps_pretty(payload))
        return 0
    print(f"Updated runner for '{tool_name}' -> {runner}")
    print(f"Bindings file: {path}")
    return 0


def _parse_set_runner_args(
    args: list[str],
) -> tuple[str, str, str | None, str | None, list[str] | None, dict[str, str] | None]:
    tool_name = None
    runner = None
    url = None
    image = None
    command = None
    env: dict[str, str] | None = None
    idx = 0
    while idx < len(args):
        item = args[idx]
        if item in {"--runner"}:
            if idx + 1 >= len(args):
                raise Namel3ssError(_missing_runner_message())
            runner = args[idx + 1]
            idx += 2
            continue
        if item.startswith("--runner="):
            runner = item.split("=", 1)[1]
            idx += 1
            continue
        if item in {"--url"}:
            if idx + 1 >= len(args):
                raise Namel3ssError(_missing_flag_value_message("--url"))
            url = args[idx + 1]
            idx += 2
            continue
        if item.startswith("--url="):
            url = item.split("=", 1)[1]
            idx += 1
            continue
        if item in {"--image"}:
            if idx + 1 >= len(args):
                raise Namel3ssError(_missing_flag_value_message("--image"))
            image = args[idx + 1]
            idx += 2
            continue
        if item.startswith("--image="):
            image = item.split("=", 1)[1]
            idx += 1
            continue
        if item in {"--command"}:
            if idx + 1 >= len(args):
                raise Namel3ssError(_missing_flag_value_message("--command"))
            command = _parse_command(args[idx + 1])
            idx += 2
            continue
        if item.startswith("--command="):
            command = _parse_command(item.split("=", 1)[1])
            idx += 1
            continue
        if item in {"--env"}:
            if idx + 1 >= len(args):
                raise Namel3ssError(_missing_flag_value_message("--env"))
            env = env or {}
            key, value = _parse_env_pair(args[idx + 1])
            env[key] = value
            idx += 2
            continue
        if item.startswith("--env="):
            env = env or {}
            key, value = _parse_env_pair(item.split("=", 1)[1])
            env[key] = value
            idx += 1
            continue
        if item.startswith("-"):
            raise Namel3ssError(_unknown_flag_message(item))
        if tool_name is None:
            tool_name = item
        else:
            raise Namel3ssError(_unknown_args_message([item]))
        idx += 1
    if not tool_name:
        raise Namel3ssError(_missing_tool_message())
    if not runner:
        raise Namel3ssError(_missing_runner_message())
    runner = runner.strip().lower()
    if runner not in {"local", "service", "container"}:
        raise Namel3ssError(_invalid_runner_message(runner))
    return tool_name, runner, url, image, command, env


def _parse_command(raw: str) -> list[str]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as err:
        raise Namel3ssError(_invalid_command_flag_message()) from err
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise Namel3ssError(_invalid_command_flag_message())
    return value


def _parse_env_pair(raw: str) -> tuple[str, str]:
    if "=" not in raw:
        raise Namel3ssError(_invalid_env_flag_message())
    key, value = raw.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        raise Namel3ssError(_invalid_env_flag_message())
    return key, value


def _missing_runner_message() -> str:
    return build_guidance_message(
        what="Runner is missing.",
        why="You must specify --runner local|service|container.",
        fix="Provide a runner value.",
        example='n3 tools set-runner "get data" --runner service --url http://127.0.0.1:8787/tools',
    )


def _missing_flag_value_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Missing value for {flag}.",
        why="The flag expects a value.",
        fix="Provide a value after the flag.",
        example=f"{flag} VALUE",
    )


def _invalid_runner_message(runner: str) -> str:
    return build_guidance_message(
        what=f"Runner '{runner}' is invalid.",
        why="Supported runners are local, service, and container.",
        fix="Use a supported runner value.",
        example='--runner local',
    )


def _invalid_command_flag_message() -> str:
    return build_guidance_message(
        what="Command must be a JSON array.",
        why="--command expects a JSON list of strings.",
        fix='Pass --command \'["python","-m","namel3ss_tools.runner"]\'.',
        example='n3 tools set-runner "tool" --runner container --command \'["python","-m","namel3ss_tools.runner"]\'',
    )


def _invalid_env_flag_message() -> str:
    return build_guidance_message(
        what="Env must be KEY=VALUE.",
        why="--env expects key=value pairs.",
        fix="Provide one --env per entry.",
        example='n3 tools set-runner "tool" --runner container --env LOG_LEVEL=info',
    )


def _next_url(binding: ToolBinding, runner: str, url: str | None) -> str | None:
    if runner == "service":
        return url or binding.url
    return None


def _next_image(binding: ToolBinding, runner: str, image: str | None) -> str | None:
    if runner == "container":
        return image or binding.image
    return None


def _next_command(binding: ToolBinding, runner: str, command: list[str] | None) -> list[str] | None:
    if runner == "container":
        return command or binding.command
    return None


def _next_env(binding: ToolBinding, runner: str, env: dict[str, str] | None) -> dict[str, str] | None:
    if runner == "container":
        return env or binding.env
    return None


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="The tools runner command does not recognize this flag.",
        fix="Remove the flag and try again.",
        example='n3 tools set-runner "get data" --runner local',
    )


def _unknown_args_message(args: list[str]) -> str:
    return build_guidance_message(
        what=f"Unknown arguments: {' '.join(args)}.",
        why="The tools runner command accepts a tool name and flags.",
        fix="Remove the extra arguments and try again.",
        example='n3 tools set-runner "get data" --runner local',
    )


def _missing_tool_message() -> str:
    return build_guidance_message(
        what="Tool name is missing.",
        why="You must specify which tool to update.",
        fix="Provide the tool name before --runner.",
        example='n3 tools set-runner "get data" --runner local',
    )


__all__ = ["run_tools_set_runner"]
