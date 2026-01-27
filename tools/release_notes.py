"""
Extract release notes for the current VERSION from CHANGELOG.md.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def read_version(repo_root: Path, version_path: Path) -> str:
    if not version_path.exists():
        raise RuntimeError(f"VERSION file not found at {version_path}.")
    return version_path.read_text(encoding="utf-8").strip()


def extract_notes(changelog: str, version: str) -> str:
    pattern = re.compile(rf"^##\s+v?{re.escape(version)}\b", re.MULTILINE)
    match = pattern.search(changelog)
    if not match:
        return (
            f"Release notes for v{version} were not found in CHANGELOG.md.\n"
            "Add a changelog entry before publishing.\n"
        )

    start = match.start()
    following = changelog[match.end() :]
    next_match = re.search(r"^##\s+", following, re.MULTILINE)
    end = match.end() + (next_match.start() if next_match else len(following))
    return changelog[start:end].strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract release notes for the current version.")
    parser.add_argument("--version-file", default="VERSION", help="Path to VERSION file.")
    parser.add_argument("--changelog", default="CHANGELOG.md", help="Path to CHANGELOG.md.")
    parser.add_argument("--output", default="release_notes.txt", help="Output path.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    version_path = (repo_root / args.version_file).resolve()
    changelog_path = (repo_root / args.changelog).resolve()

    try:
        version = read_version(repo_root, version_path)
    except RuntimeError as exc:
        print(f"Release notes failed: {exc}", file=sys.stderr)
        return 1

    if not changelog_path.exists():
        print("Release notes failed: CHANGELOG.md not found.", file=sys.stderr)
        return 1

    changelog = changelog_path.read_text(encoding="utf-8")
    notes = extract_notes(changelog, version)

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = repo_root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(notes, encoding="utf-8")
    print(f"Release notes written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
