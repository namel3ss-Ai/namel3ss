from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
src_root = repo_root / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

from namel3ss.security_hardening_scan import run_security_hardening_scan


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan repository for unsafe execution patterns and secret leaks.")
    parser.add_argument(
        "--root",
        default=str(_repo_root()),
        help="Repository root to scan. Defaults to current repository.",
    )
    parser.add_argument(
        "--json",
        dest="json_path",
        default=None,
        help="Optional file path to write a JSON report.",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    report = run_security_hardening_scan(root)
    payload = report.to_dict()
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    if args.json_path:
        json_path = Path(args.json_path)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report.status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
