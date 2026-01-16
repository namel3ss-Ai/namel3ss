from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def clean_pattern_artifacts(repo_root: Path) -> list[Path]:
    """Remove runtime artifacts from patterns/*/.namel3ss while preserving tools.yaml."""
    patterns_root = repo_root / "patterns"
    if not patterns_root.exists():
        return []
    removed: list[Path] = []
    for artifacts_dir in sorted(patterns_root.glob("**/.namel3ss")):
        if not artifacts_dir.is_dir():
            continue
        removed.extend(_clean_artifacts_dir(artifacts_dir))
    return removed


def _clean_artifacts_dir(artifacts_dir: Path) -> list[Path]:
    removed: list[Path] = []
    tools_file = artifacts_dir / "tools.yaml"
    for child in artifacts_dir.iterdir():
        if child == tools_file:
            continue
        _remove_path(child)
        removed.append(child)
    if not tools_file.exists():
        if artifacts_dir.exists():
            shutil.rmtree(artifacts_dir, ignore_errors=True)
            removed.append(artifacts_dir)
    return removed


def _remove_path(path: Path) -> None:
    if path.is_file() or path.is_symlink():
        path.unlink(missing_ok=True)
        return
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean runtime artifacts under patterns/.namel3ss.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root (defaults to project root inferred from this script).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    repo_root: Path = args.root
    removed = clean_pattern_artifacts(repo_root)
    if removed:
        print("Removed artifacts:")
        for path in removed:
            try:
                rel = path.relative_to(repo_root)
                print(f"- {rel.as_posix()}")
            except ValueError:
                print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["clean_pattern_artifacts", "main"]
