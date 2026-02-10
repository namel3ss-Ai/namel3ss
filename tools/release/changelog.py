from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

from namel3ss.determinism import canonical_json_dumps


def extract_changelog_section(changelog_text: str, version: str) -> str | None:
    pattern = re.compile(rf"^##\s+v?{re.escape(version)}\b", re.MULTILINE)
    match = pattern.search(changelog_text)
    if match is None:
        return None
    start = match.start()
    following = changelog_text[match.end() :]
    next_match = re.search(r"^##\s+", following, re.MULTILINE)
    end = match.end() + (next_match.start() if next_match else len(following))
    return changelog_text[start:end].strip() + "\n"


def build_changelog_payload(version: str, section: str) -> dict[str, object]:
    encoded = section.encode("utf-8")
    return {
        "version": version,
        "line_count": len(section.splitlines()),
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "section": section,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract deterministic changelog output for the current version.")
    parser.add_argument("--version-file", default="VERSION", help="Path to VERSION file.")
    parser.add_argument("--changelog", default="CHANGELOG.md", help="Path to changelog file.")
    parser.add_argument("--output", default=".namel3ss/release/changelog.txt", help="Output path.")
    parser.add_argument("--json", action="store_true", help="Write JSON payload instead of plain text.")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[2]
    version_path = (repo_root / args.version_file).resolve()
    changelog_path = (repo_root / args.changelog).resolve()

    if not version_path.exists():
        print(f"changelog export failed: VERSION file not found at {version_path}", file=sys.stderr)
        return 1
    if not changelog_path.exists():
        print(f"changelog export failed: CHANGELOG.md not found at {changelog_path}", file=sys.stderr)
        return 1

    version = version_path.read_text(encoding="utf-8").strip()
    changelog_text = changelog_path.read_text(encoding="utf-8")
    section = extract_changelog_section(changelog_text, version)
    if section is None:
        print(f"changelog export failed: no changelog section found for version {version}", file=sys.stderr)
        return 1

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = repo_root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.json:
        payload = build_changelog_payload(version, section)
        output_path.write_text(
            canonical_json_dumps(payload, pretty=True, drop_run_keys=False) + "\n",
            encoding="utf-8",
        )
    else:
        output_path.write_text(section, encoding="utf-8")

    print(output_path.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
