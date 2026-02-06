from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.docs.sdk import (
    generate_python_client,
    generate_typescript_client,
    generate_go_client,
    generate_rust_client,
    render_postman_collection,
)
from namel3ss.docs.spec import build_openapi_spec
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.cli.app_loader import load_program


@dataclass(frozen=True)
class _SdkParams:
    subcommand: str
    app_arg: str | None
    lang: str | None
    out_dir: Path | None
    out_file: Path | None


def run_sdk_command(args: list[str]) -> int:
    try:
        params = _parse_args(args)
        app_path = resolve_app_path(params.app_arg)
        program, _ = load_program(app_path.as_posix())
        spec = build_openapi_spec(program)
        if params.subcommand == "generate":
            if not params.lang:
                raise Namel3ssError(_missing_flag_message("--lang"))
            if params.lang not in {"python", "typescript", "go", "rust"}:
                raise Namel3ssError(_unsupported_lang_message(params.lang))
            if params.out_dir is None:
                raise Namel3ssError(_missing_flag_message("--out-dir"))
            params.out_dir.mkdir(parents=True, exist_ok=True)
            if params.lang == "python":
                content = generate_python_client(spec)
                path = params.out_dir / "client.py"
                path.write_text(content, encoding="utf-8")
                print(f"Wrote {path}")
                return 0
            if params.lang == "typescript":
                content = generate_typescript_client(spec)
                path = params.out_dir / "client.ts"
                path.write_text(content, encoding="utf-8")
                print(f"Wrote {path}")
                return 0
            if params.lang == "go":
                files = generate_go_client(spec)
                for name, content in files.items():
                    target = params.out_dir / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content, encoding="utf-8")
                    print(f"Wrote {target}")
                return 0
            if params.lang == "rust":
                files = generate_rust_client(spec)
                for name, content in files.items():
                    target = params.out_dir / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content, encoding="utf-8")
                    print(f"Wrote {target}")
                return 0
        if params.subcommand == "postman":
            if params.out_file is None:
                raise Namel3ssError(_missing_flag_message("--out"))
            content = render_postman_collection(spec)
            params.out_file.parent.mkdir(parents=True, exist_ok=True)
            params.out_file.write_text(content + "\n", encoding="utf-8")
            print(f"Wrote {params.out_file}")
            return 0
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unknown sdk command '{params.subcommand}'.",
                why="sdk supports generate and postman.",
                fix="Use n3 sdk generate or n3 sdk postman.",
                example="n3 sdk generate --lang python --out-dir sdk",
            )
        )
    except Namel3ssError as err:
        message = format_error(err, None)
        print(prepare_cli_text(message), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> _SdkParams:
    if not args:
        raise Namel3ssError(
            build_guidance_message(
                what="Missing sdk subcommand.",
                why="sdk requires generate or postman.",
                fix="Add a subcommand.",
                example="n3 sdk generate --lang python --out-dir sdk",
            )
        )
    subcommand = args[0]
    app_arg = None
    lang = None
    out_dir: Path | None = None
    out_file: Path | None = None
    i = 1
    while i < len(args):
        arg = args[i]
        if arg == "--lang":
            if i + 1 >= len(args):
                raise Namel3ssError(_missing_flag_message("--lang"))
            lang = args[i + 1]
            i += 2
            continue
        if arg == "--out-dir":
            if i + 1 >= len(args):
                raise Namel3ssError(_missing_flag_message("--out-dir"))
            out_dir = Path(args[i + 1])
            i += 2
            continue
        if arg == "--out":
            if i + 1 >= len(args):
                raise Namel3ssError(_missing_flag_message("--out"))
            out_file = Path(args[i + 1])
            i += 2
            continue
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg))
        if app_arg is None:
            app_arg = arg
            i += 1
            continue
        raise Namel3ssError(
            build_guidance_message(
                what="Too many positional arguments.",
                why="sdk accepts at most one app path.",
                fix="Provide a single app.ai path or none.",
                example="n3 sdk generate --lang python --out-dir sdk app.ai",
            )
        )
    return _SdkParams(
        subcommand=subcommand,
        app_arg=app_arg,
        lang=lang,
        out_dir=out_dir,
        out_file=out_file,
    )


def _missing_flag_message(flag: str) -> str:
    example = "n3 sdk generate --lang python --out-dir sdk"
    if flag == "--out":
        example = "n3 sdk postman --out postman.json"
    return build_guidance_message(
        what=f"{flag} flag is missing a value.",
        why="sdk requires a value for this flag.",
        fix=f"Provide a value after {flag}.",
        example=example,
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="sdk supports --lang, --out-dir, and --out.",
        fix="Remove the unsupported flag.",
        example="n3 sdk generate --lang python --out-dir sdk",
    )


def _unsupported_lang_message(lang: str) -> str:
    return build_guidance_message(
        what=f"Unsupported language '{lang}'.",
        why="sdk supports python, typescript, go, and rust.",
        fix="Use python, typescript, go, or rust.",
        example="n3 sdk generate --lang go --out-dir sdk",
    )


__all__ = ["run_sdk_command"]
