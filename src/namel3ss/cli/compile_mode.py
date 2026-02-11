from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

from namel3ss.cli.compile_entry import resolve_compile_entry_path
from namel3ss.cli.devex import parse_project_overrides
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.compilation.runner import (
    clean_compiled_artifacts,
    compile_flow_to_target,
    default_output_dir,
    list_compilation_targets,
)
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error


@dataclass(frozen=True)
class _CompileParams:
    mode: str
    app_arg: str | None
    json_mode: bool
    language: str | None
    flow_name: str | None
    out_dir: str | None
    build: bool


def run_compile_command(args: list[str]) -> int:
    try:
        overrides, remaining = parse_project_overrides(args)
        params = _parse_args(remaining)
        if params.mode == "help":
            _print_usage()
            return 0

        if params.app_arg and overrides.app_path:
            raise Namel3ssError("App path was provided twice. Use either an explicit app path or --app.")

        app_path = resolve_compile_entry_path(
            params.app_arg or overrides.app_path,
            project_root=overrides.project_root,
        )
        out_dir = _resolve_out_dir(app_path, params.out_dir)

        if params.mode == "list":
            payload = list_compilation_targets(app_path=app_path)
            payload["path"] = app_path.as_posix()
            payload["config_path"] = (app_path.parent / "compilation.yaml").as_posix()
            return _emit(payload, params.json_mode)
        if params.mode == "clean":
            payload = clean_compiled_artifacts(app_path=app_path, out_dir=out_dir)
            payload["path"] = app_path.as_posix()
            return _emit(payload, params.json_mode)

        if not params.language:
            raise Namel3ssError(_missing_flag_message("--lang"))
        if not params.flow_name:
            raise Namel3ssError(_missing_flag_message("--flow"))

        payload = compile_flow_to_target(
            app_path=app_path,
            language=params.language,
            flow_name=params.flow_name,
            out_dir=out_dir,
            build=params.build,
        )
        payload["path"] = app_path.as_posix()
        return _emit(payload, params.json_mode)
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> _CompileParams:
    if not args:
        return _CompileParams(
            mode="compile",
            app_arg=None,
            json_mode=False,
            language=None,
            flow_name=None,
            out_dir=None,
            build=False,
        )

    first = args[0].strip().lower()
    if first in {"help", "-h", "--help"}:
        return _CompileParams(
            mode="help",
            app_arg=None,
            json_mode=False,
            language=None,
            flow_name=None,
            out_dir=None,
            build=False,
        )

    mode = "compile"
    index = 0
    if first in {"list", "clean"}:
        mode = first
        index = 1

    json_mode = False
    build = False
    language = None
    flow_name = None
    out_dir = None
    positional: list[str] = []

    i = index
    while i < len(args):
        arg = args[i]
        if arg == "--json":
            json_mode = True
            i += 1
            continue
        if arg == "--build":
            build = True
            i += 1
            continue
        if arg in {"--lang", "--flow", "--out"}:
            if i + 1 >= len(args):
                raise Namel3ssError(_missing_flag_value_message(arg))
            value = args[i + 1]
            if arg == "--lang":
                language = value
            elif arg == "--flow":
                flow_name = value
            else:
                out_dir = value
            i += 2
            continue
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg, mode))
        positional.append(arg)
        i += 1

    if len(positional) > 1:
        raise Namel3ssError(_too_many_args_message(mode))

    if mode in {"list", "clean"}:
        if language is not None or flow_name is not None:
            raise Namel3ssError(_unknown_flag_message("--lang/--flow", mode))

    if mode != "compile" and build:
        raise Namel3ssError(_unknown_flag_message("--build", mode))

    return _CompileParams(
        mode=mode,
        app_arg=positional[0] if positional else None,
        json_mode=json_mode,
        language=language,
        flow_name=flow_name,
        out_dir=out_dir,
        build=build,
    )


def _resolve_out_dir(app_path: Path, raw: str | None) -> Path:
    if not raw:
        return default_output_dir(app_path)
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    return (app_path.parent / candidate).resolve()


def _emit(payload: dict[str, object], json_mode: bool) -> int:
    if json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0
    _print_human(payload)
    return 0


def _print_human(payload: dict[str, object]) -> None:
    if "items" in payload:
        items = payload.get("items")
        count = payload.get("count")
        print(f"Compilation targets: {count}")
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                print(f"- {item.get('flow_name')} -> {item.get('target')}")
        return
    if payload.get("removed") is not None:
        print(f"Cleaned: {payload.get('removed')}")
        print(f"Path: {payload.get('path')}")
        print(f"Files removed: {payload.get('files_removed')}")
        return

    print(f"Compiled flow: {payload.get('flow_name')}")
    print(f"Language: {payload.get('language')}")
    print(f"Output root: {payload.get('root')}")
    print(f"Artifact path: {payload.get('artifact_path')}")
    print(f"Source only: {payload.get('source_only')}")
    if payload.get("header_path"):
        print(f"Header path: {payload.get('header_path')}")
    files = payload.get("files")
    if isinstance(files, list):
        print(f"Files: {len(files)}")
        for path in files[:20]:
            print(f"- {path}")


def _print_usage() -> None:
    print(
        "Usage:\n"
        "  n3 compile --lang <c|python|rust|wasm> --flow <flow_name> [--out DIR] [--build] [app.ai] [--json]\n"
        "  n3 compile list [app.ai] [--json]\n"
        "  n3 compile clean [--out DIR] [app.ai] [--json]\n"
        "  n3 compile help"
    )


def _missing_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Missing required flag {flag}.",
        why="compile mode needs both --lang and --flow.",
        fix="Provide required compile flags.",
        example="n3 compile --lang rust --flow demo",
    )


def _missing_flag_value_message(flag: str) -> str:
    return build_guidance_message(
        what=f"{flag} is missing a value.",
        why="The flag requires one argument.",
        fix=f"Pass a value after {flag}.",
        example=f"n3 compile {flag} value",
    )


def _unknown_flag_message(flag: str, mode: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why=f"compile {mode} does not support this flag.",
        fix="Use --json, --out, --lang, --flow, and --build only where allowed.",
        example="n3 compile --lang c --flow demo",
    )


def _too_many_args_message(mode: str) -> str:
    return build_guidance_message(
        what=f"compile {mode} accepts one optional app path.",
        why="Extra positional arguments are not used.",
        fix="Pass one app.ai path or none.",
        example=f"n3 compile {mode} app.ai",
    )


__all__ = ["run_compile_command"]
