from __future__ import annotations

from pathlib import Path


def find_top_files(root: Path, limit: int = 10) -> list[tuple[Path, int]]:
    src_root = root / "src"
    files: list[tuple[Path, int]] = []
    if not src_root.exists():
        return files
    for path in src_root.rglob("*.py"):
        try:
            count = sum(1 for _ in path.open("r", encoding="utf-8", errors="ignore"))
        except OSError:
            continue
        files.append((path, count))
    files.sort(key=lambda x: x[1], reverse=True)
    return files[:limit]


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    top_files = find_top_files(repo_root)
    if not top_files:
        return 0
    for path, count in top_files:
        rel_path = path.relative_to(repo_root)
        print(f"{count}\t{rel_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
