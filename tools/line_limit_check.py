"""
Line length enforcement for Namel3ss source files.

Fails if any Python file under src/ exceeds the configured line limit.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, Tuple


LINE_LIMIT = 500
SRC_ROOT = Path(__file__).resolve().parent.parent / "src"


def iter_python_files(root: Path) -> Iterable[Path]:
    """Yield all Python files under the given root, sorted for stable output."""
    return sorted(root.rglob("*.py"))


def count_lines(path: Path) -> int:
    """Count lines in a file using UTF-8 decoding."""
    with path.open(encoding="utf-8") as handle:
        return sum(1 for _ in handle)


def format_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def find_offenders(files: Iterable[Path]) -> Iterable[Tuple[str, int]]:
    """Return iterable of (path, line_count) tuples that break the limit."""
    for file_path in files:
        line_count = count_lines(file_path)
        if line_count > LINE_LIMIT:
            yield format_path(file_path), line_count


def main() -> int:
    if not SRC_ROOT.exists():
        print("src directory not found; expected source files under ./src.", file=sys.stderr)
        return 1

    offenders = list(find_offenders(iter_python_files(SRC_ROOT)))
    if offenders:
        print(f"Line limit exceeded (> {LINE_LIMIT} lines per file):", file=sys.stderr)
        for path, line_count in offenders:
            print(f" - {path}: {line_count} lines", file=sys.stderr)
        return 1

    print(f"Line limit check passed (<= {LINE_LIMIT} lines per file).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

