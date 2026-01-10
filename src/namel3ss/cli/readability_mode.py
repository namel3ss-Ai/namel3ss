from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.readability.analyze import analyze_path, render_json, render_text


@dataclass(frozen=True)
class _ReadabilityParams:
    target: Path
    json_path: Path
    txt_path: Path


def run_readability_command(args: list[str]) -> int:
    params = _parse_args(args)
    report = analyze_path(params.target)
    json_text = render_json(report)
    txt_text = render_text(report) + "\n"

    params.json_path.parent.mkdir(parents=True, exist_ok=True)
    params.json_path.write_text(json_text, encoding="utf-8")
    params.txt_path.parent.mkdir(parents=True, exist_ok=True)
    params.txt_path.write_text(txt_text, encoding="utf-8")
    print(txt_text, end="")
    return 0


def _parse_args(args: list[str]) -> _ReadabilityParams:
    target_arg: str | None = None
    json_path: Path | None = None
    txt_path: Path | None = None
    idx = 0
    while idx < len(args):
        arg = args[idx]
        if arg == "--json":
            if idx + 1 >= len(args):
                raise Namel3ssError(_missing_flag_value("--json"))
            json_path = Path(args[idx + 1])
            idx += 2
            continue
        if arg.startswith("--json="):
            json_path = Path(arg.split("=", 1)[1])
            idx += 1
            continue
        if arg == "--txt":
            if idx + 1 >= len(args):
                raise Namel3ssError(_missing_flag_value("--txt"))
            txt_path = Path(args[idx + 1])
            idx += 2
            continue
        if arg.startswith("--txt="):
            txt_path = Path(arg.split("=", 1)[1])
            idx += 1
            continue
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg))
        if target_arg is None:
            target_arg = arg
            idx += 1
            continue
        raise Namel3ssError(_too_many_args_message())

    if target_arg is None:
        raise Namel3ssError(_missing_path_message())

    target = Path(target_arg)
    if not target.exists():
        raise Namel3ssError(
            build_guidance_message(
                what=f"Path not found: {target.as_posix()}",
                why="Readability needs an existing .ai file or folder.",
                fix="Pass a valid file or directory.",
                example="n3 readability app.ai",
            )
        )

    base_root = Path.cwd()
    default_dir = base_root / ".namel3ss" / "readability"
    if json_path is None:
        json_path = default_dir / "report.json"
    if txt_path is None:
        txt_path = default_dir / "report.txt"

    return _ReadabilityParams(
        target=target,
        json_path=json_path,
        txt_path=txt_path,
    )


def _missing_flag_value(flag: str) -> str:
    return build_guidance_message(
        what=f"{flag} flag is missing a value.",
        why="Readability needs a file path when the flag is present.",
        fix=f"Pass a path after {flag}.",
        example=f"n3 readability app.ai {flag} report.json",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="Readability supports --json and --txt.",
        fix="Remove the unsupported flag.",
        example="n3 readability app.ai --json report.json --txt report.txt",
    )


def _too_many_args_message() -> str:
    return build_guidance_message(
        what="Too many positional arguments.",
        why="Readability accepts a single file or folder path.",
        fix="Provide one path.",
        example="n3 readability app.ai",
    )


def _missing_path_message() -> str:
    return build_guidance_message(
        what="Missing readability target.",
        why="Readability requires a .ai file or a folder.",
        fix="Pass a path to analyze.",
        example="n3 readability app.ai",
    )


__all__ = ["run_readability_command"]
