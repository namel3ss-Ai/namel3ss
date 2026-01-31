from __future__ import annotations

import os
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _ensure_hooks_dir(git_dir: Path) -> Path:
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    return hooks_dir


def _read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return b""


def _write_hook(dest: Path, content: bytes) -> None:
    dest.write_bytes(content)
    try:
        os.chmod(dest, 0o755)
    except PermissionError:
        return


def main() -> int:
    root = _repo_root()
    git_dir = root / ".git"
    if not git_dir.exists():
        print("Failed: .git directory not found.")
        return 1

    source = root / "tools" / "git" / "pre-push"
    if not source.exists():
        print("Failed: tools/git/pre-push not found.")
        return 1

    hooks_dir = _ensure_hooks_dir(git_dir)
    dest = hooks_dir / "pre-push"

    source_bytes = source.read_bytes()
    existing = _read_bytes(dest)
    if existing == source_bytes:
        print("pre-push hook already installed.")
        return 0

    _write_hook(dest, source_bytes)
    print("pre-push hook installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
