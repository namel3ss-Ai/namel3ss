"""
Line length enforcement for Namel3ss repository files.

Fails if any Python file under src/ exceeds the default line limit or any file under
templates/ exceeds the template line limit.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, Tuple


DEFAULT_LINE_LIMIT = 500
TEMPLATE_LINE_LIMIT = 1000
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
TEMPLATES_ROOT = REPO_ROOT / "templates"


def iter_python_files(root: Path) -> Iterable[Path]:
    """Yield all Python files under the given root, sorted for stable output."""
    return sorted(root.rglob("*.py"))


def iter_template_files(root: Path) -> Iterable[Path]:
    """Yield all files under templates/, sorted for stable output."""
    return sorted(path for path in root.rglob("*") if path.is_file())


def count_lines(path: Path) -> int:
    """Count lines in a file using UTF-8 decoding."""
    with path.open(encoding="utf-8") as handle:
        return sum(1 for _ in handle)


def format_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def find_offenders(files: Iterable[Path], limit: int) -> Iterable[Tuple[str, int, int]]:
    """Return iterable of (path, line_count, limit) tuples that break the limit."""
    for file_path in files:
        line_count = count_lines(file_path)
        if line_count > limit:
            yield format_path(file_path), line_count, limit


def main() -> int:
    if not SRC_ROOT.exists():
        print("src directory not found; expected source files under ./src.", file=sys.stderr)
        return 1

    offenders: list[Tuple[str, int, int]] = []
    offenders.extend(find_offenders(iter_python_files(SRC_ROOT), DEFAULT_LINE_LIMIT))
    if TEMPLATES_ROOT.exists():
        offenders.extend(find_offenders(iter_template_files(TEMPLATES_ROOT), TEMPLATE_LINE_LIMIT))
    offenders.sort(key=lambda item: item[0])

    if offenders:
        print("Line limit exceeded:", file=sys.stderr)
        for path, line_count, limit in offenders:
            print(f" - {path}: {line_count} lines (limit {limit})", file=sys.stderr)
        return 1

    print(
        "Line limit check passed "
        f"(<= {DEFAULT_LINE_LIMIT} lines, templates <= {TEMPLATE_LINE_LIMIT} lines)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

