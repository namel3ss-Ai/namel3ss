from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
sys.dont_write_bytecode = True
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

from tools.ui_baseline_targets import build_baseline_payloads, is_allowed_target

FIX_COMMAND = "python tools/ui_baseline_refresh.py --write"


def write_baselines(payloads: dict[Path, str], *, root: Path = ROOT) -> list[Path]:
    written: list[Path] = []
    for path in sorted(payloads, key=lambda item: item.as_posix()):
        target = _resolve_target(path, root=root)
        content = payloads[path]
        existing = target.read_text(encoding="utf-8") if target.exists() else None
        if existing == content:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(path)
    return written


def check_baselines(payloads: dict[Path, str], *, root: Path = ROOT) -> list[Path]:
    drifted: list[Path] = []
    for path in sorted(payloads, key=lambda item: item.as_posix()):
        target = _resolve_target(path, root=root)
        expected = payloads[path]
        existing = target.read_text(encoding="utf-8") if target.exists() else None
        if existing != expected:
            drifted.append(path)
    return drifted


def print_drift_report(paths: Iterable[Path]) -> None:
    entries = list(paths)
    if not entries:
        return
    print("Baseline drift detected:")
    for path in entries:
        print(f"  {path.as_posix()}")
    print(f"Run: {FIX_COMMAND}")


def _resolve_target(path: Path, *, root: Path) -> Path:
    if not is_allowed_target(path):
        raise RuntimeError(f"Refusing to touch non-allowlisted baseline target: {path.as_posix()}")
    if path.is_absolute():
        return path
    return root / path


def _main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic UI baseline checker/refresh tool.")
    parser.add_argument("--check", action="store_true", help="Check baseline drift without writing files.")
    parser.add_argument("--write", action="store_true", help="Refresh baseline files deterministically.")
    args = parser.parse_args()

    if args.check and args.write:
        parser.error("Choose either --check or --write, not both.")
    if not args.check and not args.write:
        args.check = True

    payloads = build_baseline_payloads()
    if args.check:
        drifted = check_baselines(payloads)
        if drifted:
            print_drift_report(drifted)
            return 1
        print("Baselines are up to date.")
        return 0

    written = write_baselines(payloads)
    if not written:
        print("Baselines already up to date.")
        return 0
    print("Baselines refreshed:")
    for path in written:
        print(f"  {path.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
