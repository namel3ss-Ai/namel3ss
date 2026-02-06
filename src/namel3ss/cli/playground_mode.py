from __future__ import annotations

import json
from pathlib import Path
import sys

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.tutorials import (
    DEFAULT_PLAYGROUND_TIMEOUT_SECONDS,
    MAX_PLAYGROUND_TIMEOUT_SECONDS,
    check_snippet,
    run_snippet,
)


def run_playground_command(args: list[str]) -> int:
    try:
        params = _parse_args(args)
        subcommand = str(params["subcommand"])
        if subcommand == "help":
            _print_usage()
            return 0

        source = _resolve_source(
            source_text=params["source_text"],
            app_arg=params["app_arg"],
        )

        if subcommand == "check":
            payload = check_snippet(source)
            payload["action"] = "check"
            return _emit(payload, json_mode=bool(params["json_mode"]))

        if subcommand == "run":
            payload = run_snippet(
                source,
                flow_name=params["flow_name"],
                input_payload=params["input_payload"],
                timeout_seconds=float(params["timeout_seconds"]),
            )
            payload["action"] = "run"
            return _emit(payload, json_mode=bool(params["json_mode"]))

        raise Namel3ssError(_unknown_subcommand_message(subcommand))
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> dict[str, object]:
    if not args or args[0] in {"help", "-h", "--help"}:
        return {
            "subcommand": "help",
            "json_mode": False,
            "source_text": None,
            "app_arg": None,
            "flow_name": None,
            "input_payload": None,
            "timeout_seconds": DEFAULT_PLAYGROUND_TIMEOUT_SECONDS,
        }

    subcommand = args[0].strip().lower()
    if subcommand not in {"check", "run"}:
        raise Namel3ssError(_unknown_subcommand_message(subcommand))

    json_mode = False
    source_text: str | None = None
    app_arg: str | None = None
    flow_name: str | None = None
    input_payload: dict | None = None
    timeout_seconds = float(DEFAULT_PLAYGROUND_TIMEOUT_SECONDS)

    i = 1
    while i < len(args):
        token = args[i]
        if token == "--json":
            json_mode = True
            i += 1
            continue
        if token == "--source":
            if i + 1 >= len(args):
                raise Namel3ssError(_missing_value_message(token))
            source_text = args[i + 1]
            i += 2
            continue
        if token == "--flow":
            if i + 1 >= len(args):
                raise Namel3ssError(_missing_value_message(token))
            flow_name = args[i + 1]
            i += 2
            continue
        if token == "--input":
            if i + 1 >= len(args):
                raise Namel3ssError(_missing_value_message(token))
            input_payload = _parse_input_json(args[i + 1])
            i += 2
            continue
        if token == "--timeout":
            if i + 1 >= len(args):
                raise Namel3ssError(_missing_value_message(token))
            timeout_seconds = _parse_timeout(args[i + 1])
            i += 2
            continue
        if token.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(token))
        if app_arg is not None:
            raise Namel3ssError(_too_many_args_message())
        app_arg = token
        i += 1

    return {
        "subcommand": subcommand,
        "json_mode": json_mode,
        "source_text": source_text,
        "app_arg": app_arg,
        "flow_name": flow_name,
        "input_payload": input_payload,
        "timeout_seconds": timeout_seconds,
    }


def _resolve_source(*, source_text: object, app_arg: object) -> str:
    if isinstance(source_text, str) and source_text.strip():
        return source_text
    app_path = Path(resolve_app_path(app_arg if isinstance(app_arg, str) else None))
    try:
        return app_path.read_text(encoding="utf-8")
    except OSError as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Could not read playground source.",
                why=str(err),
                fix="Pass --source or a readable app.ai path.",
                example="n3 playground check app.ai",
            )
        ) from err


def _parse_input_json(text: str) -> dict:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Invalid --input payload.",
                why=f"JSON parsing failed: {err.msg}.",
                fix="Pass a JSON object string.",
                example='n3 playground run --input "{\"name\":\"Ada\"}"',
            )
        ) from err
    if not isinstance(payload, dict):
        raise Namel3ssError(
            build_guidance_message(
                what="Invalid --input payload.",
                why="playground run expects a JSON object.",
                fix="Pass a JSON object value.",
                example='n3 playground run --input "{\"name\":\"Ada\"}"',
            )
        )
    return payload


def _parse_timeout(raw: str) -> float:
    try:
        value = float(raw)
    except ValueError as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Timeout must be a number.",
                why=f"Could not parse '{raw}'.",
                fix="Provide timeout seconds as a number.",
                example="n3 playground run --timeout 5",
            )
        ) from err
    return max(0.1, min(value, float(MAX_PLAYGROUND_TIMEOUT_SECONDS)))


def _emit(payload: dict[str, object], *, json_mode: bool) -> int:
    if json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
    else:
        _print_human(payload)
    return 0 if bool(payload.get("ok")) else 1


def _print_human(payload: dict[str, object]) -> None:
    action = str(payload.get("action") or "playground")
    print(f"Playground {action}")
    print(f"  ok: {payload.get('ok')}")
    if payload.get("ok"):
        flows = payload.get("flows")
        if isinstance(flows, list):
            print(f"  flows: {', '.join(str(item) for item in flows)}")
        if payload.get("flow_name"):
            print(f"  flow: {payload.get('flow_name')}")
        if "result" in payload:
            print(f"  result: {payload.get('result')}")
        return
    error = payload.get("error")
    if error:
        print(f"  error: {error}")


def _print_usage() -> None:
    print(
        "Usage:\n"
        "  n3 playground check [app.ai] [--source TEXT] [--json]\n"
        f"  n3 playground run [app.ai] [--source TEXT] [--flow NAME] [--input JSON] [--timeout SECONDS] [--json]\n"
        f"  # default timeout: {DEFAULT_PLAYGROUND_TIMEOUT_SECONDS:.1f}s"
    )


def _unknown_subcommand_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"Unknown playground command '{subcommand}'.",
        why="Supported commands are check and run.",
        fix="Run n3 playground help.",
        example="n3 playground check --json",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="Supported flags are --source, --flow, --input, --timeout, and --json.",
        fix="Remove unsupported flags.",
        example="n3 playground run --json",
    )


def _missing_value_message(flag: str) -> str:
    return build_guidance_message(
        what=f"{flag} requires a value.",
        why="The option needs an argument.",
        fix=f"Provide a value after {flag}.",
        example=f"n3 playground run {flag} demo",
    )


def _too_many_args_message() -> str:
    return build_guidance_message(
        what="Too many positional arguments.",
        why="playground accepts at most one source path.",
        fix="Keep one path or use --source for inline code.",
        example="n3 playground check app.ai",
    )


__all__ = ["run_playground_command"]
