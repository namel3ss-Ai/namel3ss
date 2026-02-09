from __future__ import annotations

import hashlib
import runpy
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GRAMMAR_PATH = REPO_ROOT / "spec" / "grammar" / "namel3ss.grammar"
SNAPSHOT_PATH = REPO_ROOT / "src" / "namel3ss" / "parser" / "generated" / "grammar_snapshot.py"
DOC_SNAPSHOT_PATH = REPO_ROOT / "docs" / "grammar" / "current.md"


def _collect_rules(source: str) -> list[str]:
    rules: list[str] = []
    for raw in source.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        left = line.split("=", 1)[0].strip()
        if left:
            rules.append(left)
    return sorted(set(rules))


def _expected_snapshot() -> tuple[str, tuple[str, ...]]:
    source = GRAMMAR_PATH.read_text(encoding="utf-8")
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return digest, tuple(_collect_rules(source))


def _loaded_snapshot() -> tuple[str, tuple[str, ...]]:
    payload = runpy.run_path(str(SNAPSHOT_PATH))
    digest = payload.get("GRAMMAR_SHA256")
    rules = payload.get("RULE_NAMES")
    if not isinstance(digest, str):
        raise SystemExit(f"{SNAPSHOT_PATH} is missing GRAMMAR_SHA256.")
    if not isinstance(rules, tuple) or not all(isinstance(item, str) for item in rules):
        raise SystemExit(f"{SNAPSHOT_PATH} is missing RULE_NAMES tuple.")
    return digest, rules


def main() -> int:
    if not GRAMMAR_PATH.exists():
        raise SystemExit(f"Missing grammar file: {GRAMMAR_PATH}")
    if not SNAPSHOT_PATH.exists():
        raise SystemExit(f"Missing generated grammar snapshot: {SNAPSHOT_PATH}")
    if not DOC_SNAPSHOT_PATH.exists():
        raise SystemExit(f"Missing docs grammar snapshot: {DOC_SNAPSHOT_PATH}")
    expected_digest, expected_rules = _expected_snapshot()
    loaded_digest, loaded_rules = _loaded_snapshot()
    if expected_digest != loaded_digest:
        print("Grammar snapshot mismatch: digest differs.")
        print("Run: python tools/generate_parser.py")
        return 1
    if expected_rules != loaded_rules:
        print("Grammar snapshot mismatch: rule list differs.")
        print("Run: python tools/generate_parser.py")
        return 1
    print("Grammar snapshot check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
