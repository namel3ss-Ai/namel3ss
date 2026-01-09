from __future__ import annotations

import subprocess
from pathlib import Path
import sys


def repo_dirty_entries(root: Path | None = None) -> list[str]:
    repo_root = root or Path.cwd()
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("git is required for repo cleanliness checks") from exc
    if result.returncode != 0:
        raise RuntimeError(f"git status failed: {result.stderr.strip()}")
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return lines


def _main() -> int:
    dirty = repo_dirty_entries()
    if dirty:
        joined = "\n".join(dirty)
        print(f"Repository dirty:\n{joined}")
        return 1
    print("Repository clean.")
    return 0


if __name__ == "__main__":
    sys.exit(_main())


__all__ = ["repo_dirty_entries"]
