from __future__ import annotations

from dataclasses import dataclass
import json
import platform
from pathlib import Path
import subprocess
import sys
import time
from typing import Callable, Iterable

from namel3ss.release.model import GateResult, GateSpec, ReleaseReport
from namel3ss.version import get_version


RELEASE_SCHEMA_VERSION = "release.v1"

DEFAULT_GATES: tuple[GateSpec, ...] = (
    GateSpec(
        name="Parity Gate",
        tests=("tests/contract/test_parity_cli_studio.py",),
        required=True,
    ),
    GateSpec(
        name="Determinism Gate",
        tests=("tests/contract/test_determinism_wall.py",),
        required=True,
    ),
    GateSpec(
        name="Golden Suite Gate",
        tests=("tests/golden/test_golden_snapshots.py",),
        required=True,
    ),
    GateSpec(
        name="Security Gate",
        tests=(
            "tests/runtime/test_security_hardening.py",
            "tests/runtime_tools/test_no_bypass.py",
        ),
        required=True,
    ),
    GateSpec(
        name="Error Quality Gate",
        tests=("tests/contract/test_error_quality.py",),
        required=True,
    ),
    GateSpec(
        name="DevEx Gate",
        tests=(
            "tests/cli/test_cli_project_discovery.py",
            "tests/cli/test_doctor.py",
            "tests/cli/test_cli_scaffold_command.py",
        ),
        required=True,
    ),
    GateSpec(
        name="Packaging/Version/Compatibility Gate",
        tests=(
            "tests/compatibility/test_compatibility.py",
            "tests/release/test_release_version_and_template.py",
            "tests/spec/test_spec_versions.py",
            "tests/studio/test_studio_web_structure.py",
        ),
        required=True,
    ),
    GateSpec(
        name="Expression Surface Gate",
        tests=(),
        required=True,
        command=(sys.executable, "-m", "namel3ss.cli.main", "expr-check"),
    ),
    GateSpec(
        name="Eval Gate",
        tests=(),
        required=True,
        command=(
            sys.executable,
            "-m",
            "namel3ss.cli.main",
            "eval",
            "--json",
            ".namel3ss/eval_report.json",
            "--txt",
            ".namel3ss/eval_report.txt",
        ),
    ),
    GateSpec(
        name="Beta Lock Gate",
        tests=(
            "tests/beta_lock/test_beta_surfaces.py",
            "tests/beta_lock/test_agent_explain_goldens.py",
            "tests/beta_lock/test_trace_goldens.py",
            "tests/beta_lock/test_cli_goldens.py",
            "tests/beta_lock/test_handoff_preview_golden.py",
            "tests/perf_baselines/test_perf_baseline.py",
            "tests/cli/test_cli_agent_lab_template.py",
        ),
        required=True,
    ),
    GateSpec(
        name="Line Limit Gate",
        tests=(),
        required=True,
        command=(sys.executable, "tools/line_limit_check.py"),
    ),
    GateSpec(
        name="Repo Clean Gate",
        tests=(),
        required=True,
        command=(sys.executable, "-m", "namel3ss.beta_lock.repo_clean"),
    ),
)


@dataclass(frozen=True)
class GateExecution:
    exit_code: int
    duration_ms: int
    command: tuple[str, ...]
    stdout: str
    stderr: str


GateExecutor = Callable[[GateSpec, tuple[str, ...], bool], GateExecution]


def build_release_report(
    *,
    gates: Iterable[GateSpec] | None = None,
    executor: GateExecutor | None = None,
    fast: bool = False,
) -> ReleaseReport:
    gate_list = tuple(gates) if gates is not None else DEFAULT_GATES
    results: list[GateResult] = []
    if not gate_list:
        results.append(_config_missing_result())
    else:
        for gate in gate_list:
            results.append(_run_gate(gate, executor=executor, fast=fast))
    summary = _build_summary(results)
    report = ReleaseReport(
        schema_version=RELEASE_SCHEMA_VERSION,
        namel3ss_version=get_version(),
        environment=_environment_summary(),
        gates=tuple(results),
        summary=summary,
    )
    return report


def release_exit_code(report: ReleaseReport) -> int:
    return 1 if report.summary.get("status") != "pass" else 0


def write_release_report_json(report: ReleaseReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = report.as_dict()
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def render_release_text(report: ReleaseReport) -> str:
    payload = report.as_dict()
    summary = payload["summary"]
    lines = [
        f"Release check: {summary.get('status', 'unknown').upper()}",
        f"Version: {payload.get('namel3ss_version', '')}",
        f"Gates: {summary.get('passed', 0)} passed, {summary.get('failed', 0)} failed, {summary.get('missing', 0)} missing",
        "Gate results:",
    ]
    for gate in payload.get("gates", []):
        line = f"- {gate.get('name')}: {gate.get('status')} ({gate.get('code')})"
        summary_text = gate.get("summary")
        if summary_text:
            line = f"{line} {summary_text}"
        lines.append(line)
    return "\n".join(lines)


def _run_gate(gate: GateSpec, *, executor: GateExecutor | None, fast: bool) -> GateResult:
    tests = tuple(gate.tests)
    if gate.command:
        runner = executor or _run_command_gate
        execution = runner(gate, tests, fast)
        if execution.exit_code == 0:
            return GateResult(
                name=gate.name,
                required=gate.required,
                status="pass",
                code=_gate_code(gate, "pass"),
                summary="command ok",
                details=_gate_details(tests, execution),
            )
        if execution.exit_code == 5:
            return GateResult(
                name=gate.name,
                required=gate.required,
                status="missing",
                code=_gate_code(gate, "no_tests"),
                summary="command missing",
                details=_gate_details(tests, execution),
            )
        return GateResult(
            name=gate.name,
            required=gate.required,
            status="fail",
            code=_gate_code(gate, "failed"),
            summary="command failed",
            details=_gate_details(tests, execution),
        )
    if not tests:
        return _missing_tests_result(gate, reason="no_tests_configured")
    root = Path.cwd()
    missing = sorted(str((root / test).resolve()) for test in tests if not (root / test).exists())
    if missing:
        return _missing_tests_result(gate, reason="missing_files", missing=missing)
    runner = executor or _run_pytest_gate
    execution = runner(gate, tests, fast)
    if execution.exit_code == 0:
        return GateResult(
            name=gate.name,
            required=gate.required,
            status="pass",
            code=_gate_code(gate, "pass"),
            summary="pytest ok",
            details=_gate_details(tests, execution),
        )
    if execution.exit_code == 5:
        return GateResult(
            name=gate.name,
            required=gate.required,
            status="missing",
            code=_gate_code(gate, "no_tests"),
            summary="pytest collected no tests",
            details=_gate_details(tests, execution),
        )
    return GateResult(
        name=gate.name,
        required=gate.required,
        status="fail",
        code=_gate_code(gate, "failed"),
        summary="pytest failed",
        details=_gate_details(tests, execution),
    )


def _run_pytest_gate(gate: GateSpec, tests: tuple[str, ...], fast: bool) -> GateExecution:
    cmd = (sys.executable, "-m", "pytest", "-q", *tests)
    start = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    duration_ms = int((time.time() - start) * 1000)
    return GateExecution(
        exit_code=proc.returncode,
        duration_ms=duration_ms,
        command=cmd,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
    )


def _run_command_gate(gate: GateSpec, _tests: tuple[str, ...], _fast: bool) -> GateExecution:
    cmd = tuple(gate.command or ())
    start = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    duration_ms = int((time.time() - start) * 1000)
    return GateExecution(
        exit_code=proc.returncode,
        duration_ms=duration_ms,
        command=cmd,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
    )


def _gate_details(tests: tuple[str, ...], execution: GateExecution) -> dict:
    stdout_tail = _tail(execution.stdout) if execution.exit_code != 0 else ""
    stderr_tail = _tail(execution.stderr) if execution.exit_code != 0 else ""
    return {
        "tests": list(tests),
        "exit_code": execution.exit_code,
        "command": list(execution.command),
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
    }


def _tail(text: str, limit: int = 8000) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[-limit:]


def _missing_tests_result(gate: GateSpec, *, reason: str, missing: list[str] | None = None) -> GateResult:
    details = {"tests": list(gate.tests), "reason": reason}
    if missing:
        details["missing"] = missing
    return GateResult(
        name=gate.name,
        required=gate.required,
        status="missing",
        code=_gate_code(gate, "missing"),
        summary="missing gate tests",
        details=details,
    )


def _config_missing_result() -> GateResult:
    return GateResult(
        name="Release Gate Configuration",
        required=True,
        status="missing",
        code="gate.misconfigured",
        summary="no gates configured",
        details={},
    )


def _build_summary(gates: list[GateResult]) -> dict:
    counts = {"passed": 0, "failed": 0, "missing": 0}
    required_failed = 0
    for gate in gates:
        if gate.status == "pass":
            counts["passed"] += 1
        elif gate.status == "missing":
            counts["missing"] += 1
        else:
            counts["failed"] += 1
        if gate.required and gate.status != "pass":
            required_failed += 1
    status = "pass" if required_failed == 0 else "fail"
    return {
        "status": status,
        "total": len(gates),
        "passed": counts["passed"],
        "failed": counts["failed"],
        "missing": counts["missing"],
        "required_failed": required_failed,
    }


def _environment_summary() -> dict:
    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "system": platform.system(),
        "machine": platform.machine(),
    }


def _gate_code(gate: GateSpec, status: str) -> str:
    slug = gate.name.lower().replace("/", "_").replace(" ", "_")
    return f"{slug}.{status}"


__all__ = [
    "DEFAULT_GATES",
    "GateExecution",
    "GateExecutor",
    "build_release_report",
    "release_exit_code",
    "render_release_text",
    "write_release_report_json",
]
