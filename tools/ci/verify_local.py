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
    _run_command("Line limit check", [sys.executable, "tools/line_limit_check.py"])
    _run_command("Single responsibility check", [sys.executable, "tools/responsibility_check.py"])
    _run_command(
        "Compile check",
        [sys.executable, "-m", "compileall", "src", "-q"],
        env={"PYTHONDONTWRITEBYTECODE": "1"},
    )
    _run_command(
        "Pytest",
        [sys.executable, "-m", "pytest", "-q"],
        env={"PYTHONDONTWRITEBYTECODE": "1"},
    )
    _run_command("Repo clean gate", [sys.executable, "-m", "namel3ss.beta_lock.repo_clean"])
    _check_git_clean()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
