from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.why_mode import _write_human_lines
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.governance.verify import run_verify
from namel3ss.module_loader import load_project
from namel3ss.patterns.index import get_pattern, load_patterns
from namel3ss.secrets import set_audit_root, set_engine_target
from namel3ss.test_runner.parser import parse_test_file
from namel3ss.test_runner.runner import discover_test_files, run_tests
from namel3ss.utils.json_tools import dumps_pretty


@dataclass(frozen=True)
class _PatternParams:
    cmd: str
    json_mode: bool
    args: list[str]


def run_pattern(args: List[str]) -> int:
    if not args or args[0] in {"help", "-h", "--help"}:
        _print_usage()
        return 0
    json_mode = "--json" in args
    args = [arg for arg in args if arg != "--json"]
    cmd = args[0]
    params = _PatternParams(cmd=cmd, json_mode=json_mode, args=args[1:])
    if cmd == "list":
        return _run_list(params.json_mode)
    if cmd == "new":
        return _run_new(params.args, params.json_mode)
    if cmd == "verify":
        return _run_verify(params.args, params.json_mode)
    if cmd == "run":
        return _run_run(params.args, params.json_mode)
    raise Namel3ssError(
        build_guidance_message(
            what=f"Unknown pattern command '{cmd}'.",
            why="Supported commands are list, new, run, and verify.",
            fix="Run `n3 pattern help` to see usage.",
            example="n3 pattern list",
        )
    )


def _run_list(json_mode: bool) -> int:
    patterns = load_patterns()
    if json_mode:
        payload = {
            "schema_version": 1,
            "count": len(patterns),
            "patterns": [{"id": p.id, "description": p.description} for p in patterns],
        }
        print(dumps_pretty(payload))
        return 0
    lines = ["Patterns:"]
    for pattern in patterns:
        lines.append(f"- {pattern.id}: {pattern.description}")
    print("\n".join(lines))
    return 0


def _run_new(args: list[str], json_mode: bool) -> int:
    if not args:
        raise Namel3ssError(
            build_guidance_message(
                what="Pattern name is missing.",
                why="`n3 pattern new` requires a pattern id.",
                fix="Choose a pattern from `n3 pattern list`.",
                example="n3 pattern new admin-dashboard",
            )
        )
    pattern_id = args[0]
    project_name = args[1] if len(args) > 1 else pattern_id
    entry = _resolve_pattern(pattern_id)
    target = Path.cwd() / project_name
    if target.exists():
        raise Namel3ssError(
            build_guidance_message(
                what=f"Target directory already exists: {target}.",
                why="Pattern scaffolding does not overwrite existing folders.",
                fix="Choose a new project name or delete the existing folder.",
                example=f"n3 pattern new {pattern_id} my_app",
            )
        )
    shutil.copytree(entry.path, target)
    if json_mode:
        print(dumps_pretty({"status": "ok", "pattern": entry.id, "path": target.as_posix()}))
        return 0
    print(f"Created {entry.id} at {target}")
    print("Next steps:")
    print(f"  cd {target.name}")
    print("  n3 test")
    print("  n3 verify --prod")
    print("  n3 studio")
    return 0


def _run_verify(args: list[str], json_mode: bool) -> int:
    if not args:
        raise Namel3ssError(
            build_guidance_message(
                what="Pattern name is missing.",
                why="`n3 pattern verify` requires a pattern id.",
                fix="Choose a pattern from `n3 pattern list`.",
                example="n3 pattern verify admin-dashboard",
            )
        )
    entry = _resolve_pattern(args[0])
    test_report = _run_tests(entry.path)
    verify_report = _run_verify_report(entry.path)
    status = "ok" if test_report["status"] == "ok" and verify_report.get("status") == "ok" else "fail"
    payload = {
        "schema_version": 1,
        "pattern": entry.id,
        "status": status,
        "tests": test_report,
        "verify": verify_report,
    }
    if json_mode:
        print(dumps_pretty(payload))
        return 0 if status == "ok" else 1
    lines = [f"Pattern {entry.id} verification: {status}"]
    lines.append(f"- tests: {test_report['status']}")
    lines.append(f"- verify: {verify_report.get('status', 'unknown')}")
    _write_human_lines(lines)
    return 0 if status == "ok" else 1


def _run_run(args: list[str], json_mode: bool) -> int:
    if not args:
        raise Namel3ssError(
            build_guidance_message(
                what="Pattern name is missing.",
                why="`n3 pattern run` needs a pattern id.",
                fix="Choose a pattern from `n3 pattern list`.",
                example="n3 pattern run admin-dashboard",
            )
        )
    entry = _resolve_pattern(args[0])
    message = [
        f"Pattern '{entry.id}' is a template.",
        f"Scaffold it locally with: n3 pattern new {entry.id} my_app",
        "Then run: n3 studio or n3 app.ai",
    ]
    if json_mode:
        print(dumps_pretty({"status": "ok", "message": message}))
        return 0
    print("\n".join(message))
    return 0


def _resolve_pattern(pattern_id: str):
    patterns = load_patterns()
    entry = get_pattern(pattern_id, patterns)
    if entry is None:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Pattern '{pattern_id}' was not found.",
                why="The patterns index does not include that id.",
                fix="Run `n3 pattern list` to see available patterns.",
                example="n3 pattern list",
            )
        )
    if not entry.path.exists():
        raise Namel3ssError(
            build_guidance_message(
                what=f"Pattern '{entry.id}' directory is missing.",
                why=f"Expected {entry.path.as_posix()} to exist.",
                fix="Reinstall the patterns catalog or update N3_PATTERNS_PATH.",
                example="N3_PATTERNS_PATH=./patterns",
            )
        )
    return entry


def _run_tests(pattern_root: Path) -> dict:
    app_path = pattern_root / "app.ai"
    if not app_path.exists():
        raise Namel3ssError(f"Missing app.ai in {pattern_root}")
    test_paths = discover_test_files(pattern_root)
    if not test_paths:
        return {"status": "ok", "tests": []}
    test_files = [parse_test_file(path) for path in test_paths]
    extra_uses = [use for tf in test_files for use in tf.uses]
    project = load_project(app_path, extra_uses=extra_uses)
    results = run_tests(project, test_files)
    payload = {
        "status": "ok" if all(r.status == "pass" for r in results) else "fail",
        "tests": [
            {
                "name": r.name,
                "file": r.file,
                "status": r.status,
                "duration_ms": round(r.duration_ms, 2),
                **({"error": r.error} if r.error else {}),
            }
            for r in results
        ],
    }
    return payload


def _run_verify_report(pattern_root: Path) -> dict:
    app_path = resolve_app_path(str(pattern_root / "app.ai"))
    set_engine_target("local")
    set_audit_root(pattern_root)
    return run_verify(app_path, target="local", prod=True)


def _print_usage() -> None:
    usage = """Usage:
  n3 pattern list            # list available patterns
  n3 pattern new name target # scaffold a pattern project
  n3 pattern run name        # print run instructions
  n3 pattern verify name     # run tests and verify for a pattern
  n3 pattern command --json  # JSON output for any command
  Notes:
    flags are optional unless stated
"""
    print(usage.strip())


__all__ = ["run_pattern"]
