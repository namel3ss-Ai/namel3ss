from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

from namel3ss.evals.loader import load_eval_suite
from namel3ss.evals.runner import render_eval_text, run_eval_suite
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


@dataclass(frozen=True)
class _EvalParams:
    suite_path: Path
    json_path: Path
    txt_path: Path | None
    fast: bool


def run_eval_command(args: list[str]) -> int:
    params = _parse_args(args)
    suite = load_eval_suite(params.suite_path)
    report = run_eval_suite(suite, fast=params.fast)
    payload = json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n"
    params.json_path.parent.mkdir(parents=True, exist_ok=True)
    params.json_path.write_text(payload, encoding="utf-8")
    text = render_eval_text(report)
    if params.txt_path is not None:
        params.txt_path.parent.mkdir(parents=True, exist_ok=True)
        params.txt_path.write_text(text + "\n", encoding="utf-8")
    if not params.fast:
        print(text)
    return 0 if report.status == "pass" else 1


def _parse_args(args: list[str]) -> _EvalParams:
    json_path = Path.cwd() / "eval_report.json"
    txt_path: Path | None = None
    fast = False
    suite_path: Path | None = None
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
        if suite_path is not None:
            raise Namel3ssError(_too_many_args_message())
        suite_path = Path(arg)
        idx += 1
    suite_path = suite_path or Path.cwd() / "evals"
    return _EvalParams(suite_path=suite_path, json_path=json_path, txt_path=txt_path, fast=fast)


def _missing_flag_value(flag: str) -> str:
    return build_guidance_message(
        what=f"{flag} flag is missing a value.",
        why="eval requires a file path when the flag is present.",
        fix=f"Pass a path after {flag}.",
        example=f"n3 eval {flag} eval_report.json",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="eval supports --json, --txt, and --fast.",
        fix="Remove the unsupported flag.",
        example="n3 eval --json eval_report.json",
    )


def _too_many_args_message() -> str:
    return build_guidance_message(
        what="eval accepts at most one positional path.",
        why="Provide a suite.json file or a directory containing suite.json.",
        fix="Remove the extra arguments.",
        example="n3 eval evals",
    )


__all__ = ["run_eval_command"]
