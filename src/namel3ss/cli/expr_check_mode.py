from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


EXPR_CHECK_SCHEMA_VERSION = "expression.surface.v1"
EXPR_CHECK_TESTS = (
    "tests/contract/test_expression_surface_contract.py",
    "tests/runtime/test_expression_explain_trace.py",
    "tests/studio/test_studio_formulas_api.py",
)


@dataclass(frozen=True)
class _ExprCheckParams:
    json_path: Path | None


def run_expr_check_command(args: list[str]) -> int:
    params = _parse_args(args)
    report = _run_expr_checks()
    payload = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    if params.json_path is not None:
        params.json_path.parent.mkdir(parents=True, exist_ok=True)
        params.json_path.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if report.get("status") == "pass" else 1


def _run_expr_checks() -> dict:
    cmd = (sys.executable, "-m", "pytest", "-q", *EXPR_CHECK_TESTS)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    status = "pass" if proc.returncode == 0 else "fail"
    return {
        "schema_version": EXPR_CHECK_SCHEMA_VERSION,
        "status": status,
        "exit_code": proc.returncode,
        "tests": list(EXPR_CHECK_TESTS),
    }


def _parse_args(args: list[str]) -> _ExprCheckParams:
    json_path: Path | None = None
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
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg))
        raise Namel3ssError(_too_many_args_message())
    return _ExprCheckParams(json_path=json_path)


def _missing_flag_value(flag: str) -> str:
    return build_guidance_message(
        what=f"{flag} flag is missing a value.",
        why="expr-check requires a file path when the flag is present.",
        fix=f"Pass a path after {flag}.",
        example=f"n3 expr-check {flag} expr_report.json",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="expr-check supports only --json.",
        fix="Remove the unsupported flag.",
        example="n3 expr-check --json expr_report.json",
    )


def _too_many_args_message() -> str:
    return build_guidance_message(
        what="expr-check does not accept positional arguments.",
        why="All arguments are flags.",
        fix="Remove the extra arguments.",
        example="n3 expr-check --json expr_report.json",
    )


__all__ = ["run_expr_check_command"]
