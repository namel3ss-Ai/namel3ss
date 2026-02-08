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


def test_console_script_help_entrypoint() -> None:
    """Installed `n3 --help` script must succeed and print the same usage surface."""
    n3_script = _resolve_n3_script()
    result = _run_command([n3_script, "--help"])
    _assert_usage_output(result.stdout)
