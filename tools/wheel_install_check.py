"""
Verify sdist contents and smoke-test wheel installs in a clean venv.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tarfile
import tempfile
import venv
from pathlib import Path


def format_command(cmd: list[str]) -> str:
    formatted: list[str] = []
    for arg in cmd:
        if os.path.isabs(arg):
            formatted.append(Path(arg).name)
        else:
            formatted.append(arg)
    return " ".join(formatted)


def run(cmd: list[str], *, env: dict[str, str] | None = None, cwd: Path | None = None) -> None:
    result = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        suffix = f"\n{message}" if message else ""
        raise RuntimeError(f"Command failed: {format_command(cmd)}{suffix}")


def read_version(version_path: Path) -> str:
    if not version_path.exists():
        raise RuntimeError("VERSION file not found.")
    return version_path.read_text(encoding="utf-8").strip()


def find_artifact(dist_dir: Path, pattern: str, kind: str, version: str) -> Path:
    candidates = sorted(dist_dir.glob(pattern))
    if not candidates:
        raise RuntimeError(f"No {kind} artifacts found in dist.")
    versioned = [candidate for candidate in candidates if version in candidate.name]
    if not versioned:
        raise RuntimeError(f"No {kind} artifacts found for version {version}.")
    return versioned[0]


def check_sdist_contains_safeio(sdist_path: Path) -> None:
    with tarfile.open(sdist_path, "r:gz") as archive:
        members = [member.name for member in archive.getmembers()]
    if not any(name.endswith("src/namel3ss_safeio.py") for name in members):
        raise RuntimeError("sdist is missing src/namel3ss_safeio.py.")


def venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def build_env(dist_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "PIP_NO_INPUT": "1",
            "PIP_NO_CACHE_DIR": "1",
            "PIP_NO_PYTHON_VERSION_WARNING": "1",
            "PIP_NO_INDEX": "1",
            "PIP_FIND_LINKS": str(dist_dir),
        }
    )
    return env


def main() -> int:
    parser = argparse.ArgumentParser(description="Check wheel install and sdist contents.")
    parser.add_argument("--dist-dir", default="dist", help="Directory containing build artifacts.")
    parser.add_argument("--version-file", default="VERSION", help="Path to VERSION file.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    dist_dir = (repo_root / args.dist_dir).resolve()
    version_path = (repo_root / args.version_file).resolve()

    try:
        version = read_version(version_path)
        if not dist_dir.exists():
            raise RuntimeError("dist directory not found. Run `python -m build` first.")
        wheel_path = find_artifact(dist_dir, "*.whl", "wheel", version)
        sdist_path = find_artifact(dist_dir, "*.tar.gz", "sdist", version)
        check_sdist_contains_safeio(sdist_path)

        with tempfile.TemporaryDirectory() as temp_dir:
            venv_dir = Path(temp_dir) / "venv"
            venv.EnvBuilder(with_pip=True, clear=True).create(venv_dir)
            python_bin = venv_python(venv_dir)
            env = build_env(dist_dir)
            run([str(python_bin), "-m", "pip", "install", str(wheel_path)], env=env)
            run([str(python_bin), "-c", "import namel3ss_safeio"], env=env)
            run([str(python_bin), "-m", "namel3ss", "--help"], env=env)
    except RuntimeError as exc:
        print(f"Wheel install check failed: {exc}", file=sys.stderr)
        return 1

    print("Wheel install check ok.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
