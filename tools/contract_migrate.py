from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TARGETS = {
    "grammar": REPO_ROOT / "docs" / "language" / "grammar_contract.md",
    "schema": REPO_ROOT / "docs" / "trace-schema.md",
    "templates": REPO_ROOT / "docs" / "templates.md",
}


def _normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _relative_path(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _resolve_target(kind: str, path: str | None) -> Path:
    if path:
        target = Path(path).resolve()
    else:
        if kind not in DEFAULT_TARGETS:
            raise ValueError(f"Unknown kind: {kind}")
        target = DEFAULT_TARGETS[kind]
    try:
        target.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise ValueError("Target must be inside the repository root") from exc
    if not target.exists():
        raise ValueError(f"Target not found: {_relative_path(target)}")
    return target


def build_plan(kind: str, path: str | None) -> dict:
    target = _resolve_target(kind, path)
    text = _normalize_text(target.read_text(encoding="utf-8"))
    digest = _hash_text(text)
    return {
        "kind": kind,
        "target": _relative_path(target),
        "status": "none",
        "before_hash": digest,
        "after_hash": digest,
        "changes": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Contract migration planner")
    parser.add_argument("--kind", choices=sorted(DEFAULT_TARGETS.keys()), required=True)
    parser.add_argument("--path", default=None)
    args = parser.parse_args()

    try:
        plan = build_plan(args.kind, args.path)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(json.dumps(plan, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
