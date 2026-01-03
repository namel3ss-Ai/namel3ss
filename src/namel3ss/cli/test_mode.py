from __future__ import annotations

from time import perf_counter

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.cli.devex import parse_project_overrides
from namel3ss.cli.app_path import resolve_app_path
from namel3ss.config.dotenv import apply_dotenv, load_dotenv_for_path
from namel3ss.module_loader import load_project
from namel3ss.test_runner.parser import parse_test_file
from namel3ss.test_runner.runner import discover_test_files, run_tests
from namel3ss.utils.json_tools import dumps_pretty


def run_test_command(args: list[str]) -> int:
    overrides, remaining = parse_project_overrides(args)
    json_mode = "--json" in remaining
    tail = [arg for arg in remaining if arg != "--json"]
    if tail:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unknown arguments: {' '.join(tail)}.",
                why="test only accepts --json and optional --app/--project overrides.",
                fix="Remove the extra arguments and try again.",
                example="n3 test --json",
            )
        )
    app_path = resolve_app_path(overrides.app_path, project_root=overrides.project_root)
    root = app_path.parent
    apply_dotenv(load_dotenv_for_path(str(app_path)))
    test_paths = discover_test_files(root)
    if not test_paths:
        payload = {"status": "ok", "tests": []}
        if json_mode:
            print(dumps_pretty(payload))
        else:
            print("No tests found under tests/")
        return 0

    test_files = [parse_test_file(path) for path in test_paths]
    extra_uses = [use for tf in test_files for use in tf.uses]

    start = perf_counter()
    project = load_project(app_path, extra_uses=extra_uses)
    results = run_tests(project, test_files)
    duration_ms = (perf_counter() - start) * 1000

    passed = sum(1 for r in results if r.status == "pass")
    failed = sum(1 for r in results if r.status != "pass")

    if json_mode:
        payload = {
            "status": "ok" if failed == 0 else "fail",
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
        print(dumps_pretty(payload))
        return 0 if failed == 0 else 1

    for r in results:
        status = "PASS" if r.status == "pass" else "FAIL"
        print(f"{status} {r.name} duration {r.duration_ms:.2f}ms")
        if r.error:
            print(f"  {r.error}")
    print(f"Summary: {passed} passed, {failed} failed, {len(results)} total duration {duration_ms:.2f}ms")
    return 0 if failed == 0 else 1
