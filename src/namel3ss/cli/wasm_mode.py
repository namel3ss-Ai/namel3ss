from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.compilation.wasm_runner import run_wasm_module
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error


@dataclass(frozen=True)
class _WasmParams:
    subcommand: str
    module_path: str | None
    input_json: str
    json_mode: bool


def run_wasm_command(args: list[str]) -> int:
    try:
        params = _parse_args(args)
        if params.subcommand == "help":
            _print_usage()
            return 0
        if params.subcommand != "run":
            raise Namel3ssError(_unknown_subcommand_message(params.subcommand))
        if not params.module_path:
            raise Namel3ssError(_missing_module_message())

        payload = run_wasm_module(Path(params.module_path), input_json=params.input_json)
        return _emit(payload, params.json_mode)
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> _WasmParams:
    if not args:
        return _WasmParams(subcommand="help", module_path=None, input_json="{}", json_mode=False)

    first = args[0].strip().lower()
    if first in {"help", "-h", "--help"}:
        return _WasmParams(subcommand="help", module_path=None, input_json="{}", json_mode=False)
    if first != "run":
        return _WasmParams(subcommand=first, module_path=None, input_json="{}", json_mode=False)

    json_mode = False
    module_path = None
    input_json = "{}"

    i = 1
    while i < len(args):
        arg = args[i]
        if arg == "--json":
            json_mode = True
            i += 1
            continue
        if arg == "--input":
            if i + 1 >= len(args):
                raise Namel3ssError(_missing_flag_value_message("--input"))
            input_json = args[i + 1]
            i += 2
            continue
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg))
        if module_path is None:
            module_path = arg
            i += 1
            continue
        raise Namel3ssError(_too_many_args_message())

    return _WasmParams(subcommand="run", module_path=module_path, input_json=input_json, json_mode=json_mode)


def _emit(payload: dict[str, object], json_mode: bool) -> int:
    if json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0
    print(f"Wasm runtime: {payload.get('runtime')}")
    print(f"Module: {payload.get('module')}")
    print(f"Output: {payload.get('output')}")
    stderr = payload.get("stderr")
    if stderr:
        print(f"Stderr: {stderr}")
    return 0


def _print_usage() -> None:
    print(
        "Usage:\n"
        "  n3 wasm run <module.wasm> --input <json> [--json]\n"
        "  n3 wasm help"
    )


def _unknown_subcommand_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"Unknown wasm command '{subcommand}'.",
        why="Supported subcommands are run and help.",
        fix="Use n3 wasm run <module.wasm> --input <json>.",
        example="n3 wasm run module.wasm --input '{}'",
    )


def _missing_module_message() -> str:
    return build_guidance_message(
        what="Module path is missing.",
        why="n3 wasm run needs a .wasm file path.",
        fix="Pass the path to the wasm module.",
        example="n3 wasm run module.wasm --input '{}'",
    )


def _missing_flag_value_message(flag: str) -> str:
    return build_guidance_message(
        what=f"{flag} is missing a value.",
        why="This flag requires one argument.",
        fix=f"Pass a value after {flag}.",
        example="n3 wasm run module.wasm --input '{\"a\":2}'",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="Supported wasm run flags are --input and --json.",
        fix="Remove the unsupported flag.",
        example="n3 wasm run module.wasm --input '{}'",
    )


def _too_many_args_message() -> str:
    return build_guidance_message(
        what="wasm run accepts one module path.",
        why="Additional positional arguments are not used.",
        fix="Pass only one .wasm file path.",
        example="n3 wasm run module.wasm --input '{}'",
    )


__all__ = ["run_wasm_command"]
