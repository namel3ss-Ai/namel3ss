from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.executor.api import execute_program_flow
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.test_runner.types import (
    ExpectErrorContainsStep,
    ExpectValueContainsStep,
    ExpectValueIsStep,
    RunFlowStep,
    TestFile,
    TestResult,
)


def discover_test_files(root: Path) -> List[Path]:
    tests_dir = root / "tests"
    if not tests_dir.exists():
        return []
    files = sorted(tests_dir.rglob("*_test.ai"), key=lambda p: p.as_posix())
    return [path for path in files if path.is_file()]


def run_tests(project, test_files: List[TestFile]) -> List[TestResult]:
    results: list[TestResult] = []
    for test_file in test_files:
        alias_map = _normalize_uses(test_file.uses, file_path=test_file.path)
        for test in test_file.tests:
            result = _run_test_case(project, test_file, test, alias_map)
            results.append(result)
    return results


def _run_test_case(project, test_file: TestFile, test, alias_map: Dict[str, str]) -> TestResult:
    start = time.perf_counter()
    status = "pass"
    error = None
    state: dict = {}
    store = MemoryStore()
    last_value = None
    last_error = None
    for step in test.steps:
        if isinstance(step, RunFlowStep):
            try:
                flow_name = _resolve_flow_name(step.flow_name, alias_map)
                result = execute_program_flow(
                    project.program,
                    flow_name,
                    state=state,
                    input=step.input_data,
                    store=store,
                )
                state = result.state
                last_value = result.last_value
                last_error = None
            except Namel3ssError as err:
                last_value = None
                last_error = str(err)
        elif isinstance(step, ExpectValueIsStep):
            if last_error is not None:
                status = "fail"
                error = f"Expected value, but last run failed: {last_error}"
                break
            if last_value != step.expected:
                status = "fail"
                error = f"Expected value {step.expected!r}, got {last_value!r}"
                break
        elif isinstance(step, ExpectValueContainsStep):
            if last_error is not None:
                status = "fail"
                error = f"Expected value, but last run failed: {last_error}"
                break
            if not isinstance(last_value, str):
                status = "fail"
                error = f"Expected a text value, got {type(last_value).__name__}"
                break
            if step.expected not in last_value:
                status = "fail"
                error = f"Expected value to contain {step.expected!r}, got {last_value!r}"
                break
        elif isinstance(step, ExpectErrorContainsStep):
            if last_error is None:
                status = "fail"
                error = "Expected an error, but the last run succeeded"
                break
            if step.expected not in last_error:
                status = "fail"
                error = f"Expected error to contain {step.expected!r}, got {last_error!r}"
                break
        else:
            status = "fail"
            error = "Unsupported test step"
            break

    duration_ms = (time.perf_counter() - start) * 1000
    name = f"{Path(test_file.path).name}::{test.name}"
    return TestResult(
        name=name,
        file=test_file.path,
        status=status,
        duration_ms=duration_ms,
        error=error,
    )


def _normalize_uses(uses, *, file_path: str) -> Dict[str, str]:
    alias_map: Dict[str, str] = {}
    for use in uses:
        if use.alias in alias_map and alias_map[use.alias] != use.module:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Duplicate alias '{use.alias}' in test file.",
                    why="Each alias must be unique per test file.",
                    fix="Pick a different alias for the second module.",
                    example='use "inventory" as inv',
                )
            )
        alias_map[use.alias] = use.module
    return alias_map


def _resolve_flow_name(raw: str, alias_map: Dict[str, str]) -> str:
    if "." in raw:
        prefix, rest = raw.split(".", 1)
        if prefix in alias_map:
            return f"{alias_map[prefix]}.{rest}"
        if alias_map:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unknown module alias '{prefix}' in test file.",
                    why="The test file did not declare this alias with a use statement.",
                    fix=f'Add `use "<module>" as {prefix}` at the top of the test file.',
                    example=f'use "inventory" as {prefix}',
                )
            )
    return raw
