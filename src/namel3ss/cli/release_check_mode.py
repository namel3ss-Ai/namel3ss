from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.release.runner import (
    build_release_report,
    release_exit_code,
    render_release_text,
    write_release_report_json,
)


@dataclass(frozen=True)
class _ReleaseParams:
    json_path: Path
    txt_path: Path | None
    fast: bool


def run_release_check_command(args: list[str]) -> int:
    params = _parse_args(args)
    report = build_release_report(fast=params.fast)
    write_release_report_json(report, params.json_path)
    if params.txt_path:
        params.txt_path.parent.mkdir(parents=True, exist_ok=True)
        params.txt_path.write_text(render_release_text(report) + "\n", encoding="utf-8")
    if not params.fast:
        print(render_release_text(report))
    return release_exit_code(report)


def _parse_args(args: list[str]) -> _ReleaseParams:
    json_path = Path.cwd() / "release_report.json"
    txt_path: Path | None = None
    fast = False
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
        if arg == "--fast":
            fast = True
            idx += 1
            continue
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg))
        raise Namel3ssError(_too_many_args_message())
    return _ReleaseParams(json_path=json_path, txt_path=txt_path, fast=fast)


def _missing_flag_value(flag: str) -> str:
    return build_guidance_message(
        what=f"{flag} flag is missing a value.",
        why="release-check requires a file path when the flag is present.",
        fix=f"Pass a path after {flag}.",
        example=f"n3 release-check {flag} release_report.json",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="release-check supports --json, --txt, and --fast.",
        fix="Remove the unsupported flag.",
        example="n3 release-check --json release_report.json",
    )


def _too_many_args_message() -> str:
    return build_guidance_message(
        what="release-check does not accept positional arguments.",
        why="All arguments are flags.",
        fix="Remove the extra arguments.",
        example="n3 release-check --json release_report.json",
    )


__all__ = ["run_release_check_command"]
