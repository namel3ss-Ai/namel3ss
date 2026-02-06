from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _print_header() -> None:
    print("Local verification")
    print("Checks:")


def _format_command(cmd: list[str], env: dict[str, str] | None) -> str:
    prefix = ""
    if env and "PYTHONDONTWRITEBYTECODE" in env:
        prefix = f"PYTHONDONTWRITEBYTECODE={env['PYTHONDONTWRITEBYTECODE']} "
    return prefix + " ".join(cmd)


def _run_command(label: str, cmd: list[str], env: dict[str, str] | None = None) -> None:
    print(f"- {label}")
    print(f"$ {_format_command(cmd, env)}")
    sys.stdout.flush()
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    try:
        result = subprocess.run(cmd, env=merged_env)
    except FileNotFoundError:
        print(f"Failed: command not found: {cmd[0]}")
        raise SystemExit(1)
    if result.returncode != 0:
        print(f"Failed: {label}")
        raise SystemExit(result.returncode)


def _check_git_clean() -> None:
    cmd = ["git", "status", "--porcelain"]
    print("- Git status clean")
    print(f"$ {' '.join(cmd)}")
    sys.stdout.flush()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        print("Failed: git is required for the clean check.")
        raise SystemExit(1)
    output = (result.stdout or "").strip()
    if result.returncode != 0:
        print("Failed: git status returned a non-zero exit code.")
        if output:
            print(output)
        raise SystemExit(result.returncode)
    if output:
        print("Failed: working tree is not clean.")
        print(output)
        raise SystemExit(1)


def main() -> int:
    os.chdir(_repo_root())
    _print_header()
    _run_command("Security hardening scan", [sys.executable, "tools/security_hardening_scan.py"])
    _run_command("Line limit check", [sys.executable, "tools/line_limit_check.py"])
    _run_command("Single responsibility check", [sys.executable, "tools/responsibility_check.py"])
    _run_command("Code audit report check", [sys.executable, "scripts/audit_codebase.py", "--check"])
    _run_command(
        "Baseline metrics check",
        [sys.executable, "scripts/measure_baseline.py", "--check", "--timing", "deterministic"],
    )
    _run_command(
        "Compile check",
        [sys.executable, "-m", "compileall", "src", "-q"],
        env={"PYTHONDONTWRITEBYTECODE": "1"},
    )
    _run_command(
        "CLI entrypoint help",
        [sys.executable, "-m", "namel3ss", "--help"],
        env={"PYTHONDONTWRITEBYTECODE": "1"},
    )
    _run_command(
        "CLI install gate tests",
        [sys.executable, "-m", "pytest", "-q", "tests/test_cli_install.py"],
        env={"PYTHONDONTWRITEBYTECODE": "1"},
    )
    _run_command(
        "Pytest",
        [sys.executable, "-m", "pytest", "-q"],
        env={"PYTHONDONTWRITEBYTECODE": "1"},
    )
    _run_command(
        "Multimodal deterministic suite",
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/runtime/test_ai_multimodal_input.py",
            "tests/ir/test_lowering_capabilities.py",
            "tests/spec_check/test_multimodal_required_capabilities.py",
        ],
        env={"PYTHONDONTWRITEBYTECODE": "1"},
    )
    _run_command(
        "Training deterministic suite",
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/cli/test_cli_train_command.py",
            "tests/training/test_training_runner.py",
            "tests/training/test_dataset_utils.py",
            "tests/scripts/test_convert_state_to_training_dataset.py",
        ],
        env={"PYTHONDONTWRITEBYTECODE": "1"},
    )
    _run_command(
        "Provider ecosystem suite",
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/providers/test_capabilities.py",
            "tests/providers/test_pack_registry.py",
            "tests/runtime/test_provider_pack_runtime.py",
            "tests/studio/test_studio_providers_api.py",
            "tests/studio/test_studio_provider_setup_panel.py",
            "tests/docs/test_providers_supported_doc.py",
            "tests/docs/test_providers_doc_contract.py",
            "tests/pkg/test_pkg_index.py",
        ],
        env={"PYTHONDONTWRITEBYTECODE": "1"},
    )
    _run_command(
        "Streaming suite",
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/parser/test_ai_parse.py",
            "tests/ir/test_lowering_capabilities.py",
            "tests/runtime/test_ai_streaming.py",
            "tests/spec_check/test_streaming_required_capabilities.py",
            "tests/studio/test_studio_minimal_routes.py",
            "tests/docs/test_streaming_doc_contract.py",
        ],
        env={"PYTHONDONTWRITEBYTECODE": "1"},
    )
    _run_command("Repo clean gate", [sys.executable, "-m", "namel3ss.beta_lock.repo_clean"])
    _check_git_clean()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
