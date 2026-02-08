from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


def _assert_usage_output(output: str) -> None:
    assert "Usage:" in output
    assert "n3 <command> [file.ai]" in output
    assert "python -m namel3ss <command> [file.ai]" in output


def _run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, capture_output=True, text=True, check=True)
    except FileNotFoundError as exc:  # pragma: no cover - platform/package failure branch
        pytest.fail(f"CLI command not found: {command[0]} ({exc})")


def _resolve_n3_script() -> str:
    scripts_dir = Path(sys.executable).resolve().parent
    candidates = (
        scripts_dir / "n3",
        scripts_dir / "n3.exe",
        scripts_dir / "n3-script.py",
    )
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    on_path = shutil.which("n3")
    if on_path:
        return on_path
    pytest.fail("Could not find installed n3 console script in interpreter scripts directory or PATH.")


def test_python_module_help_entrypoint() -> None:
    """`python -m namel3ss --help` must succeed and print top-level usage."""
    result = _run_command([sys.executable, "-m", "namel3ss", "--help"])
    _assert_usage_output(result.stdout)


def test_python_module_version_entrypoint() -> None:
    """`python -m namel3ss --version` must succeed and print package/version text."""
    result = _run_command([sys.executable, "-m", "namel3ss", "--version"])
    output = result.stdout.strip()
    assert output
    assert "namel3ss" in output.lower()


def test_console_script_help_entrypoint() -> None:
    """Installed `n3 --help` script must succeed and print the same usage surface."""
    n3_script = _resolve_n3_script()
    result = _run_command([n3_script, "--help"])
    _assert_usage_output(result.stdout)


def test_console_script_version_entrypoint() -> None:
    """Installed `n3 --version` script must succeed and print package/version text."""
    n3_script = _resolve_n3_script()
    result = _run_command([n3_script, "--version"])
    output = result.stdout.strip()
    assert output
    assert "namel3ss" in output.lower()


def test_cli_install_gate_workflow_contract() -> None:
    """
    Keep the CI cli-install-gate deterministic across OSes.

    This catches regressions where:
    - the gate points to a missing CLI test path
    - Windows writes logs into a different directory than artifact upload
    """
    repo_root = Path(__file__).resolve().parents[1]
    ci_workflow = (repo_root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "python -m pytest -q tests/test_cli_install.py" in ci_workflow
    assert '$logDir = ".namel3ss/ci"' in ci_workflow
    assert "path: .namel3ss/ci/" in ci_workflow
    assert ".namel3ss\\\\ci" not in ci_workflow


def test_local_verify_includes_cli_gate_checks() -> None:
    """
    Ensure local verification runs CLI install checks before push.
    """
    repo_root = Path(__file__).resolve().parents[1]
    verify_local = (repo_root / "tools" / "ci" / "verify_local.py").read_text(encoding="utf-8")
    assert "tests/test_cli_install.py" in verify_local
    assert '["n3", "--version"]' in verify_local
    assert '["n3", "--help"]' in verify_local
    assert '[sys.executable, "-m", "namel3ss", "--version"]' in verify_local
    assert '[sys.executable, "-m", "namel3ss", "--help"]' in verify_local
