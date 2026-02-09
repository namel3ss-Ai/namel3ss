from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
sys.dont_write_bytecode = True
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
from typing import Iterable

from namel3ss.determinism import canonical_json_dumps
from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse
from namel3ss.ui.manifest import build_manifest
from namel3ss.validation import ValidationMode

from tests.ui.ui_manifest_baseline_harness import (
    BASELINE_FIXTURES_DIR,
    baseline_cases,
    build_case_snapshot,
)


LAYOUT_FIXTURE = Path("tests/fixtures/ui_layout_manifest_app.ai")
LAYOUT_GOLDEN = Path("tests/fixtures/ui_layout_manifest_golden.json")
LAYOUT_STATE = {
    "show_top": True,
    "show_main": False,
    "show_drawer": True,
}

THEME_FIXTURE = Path("tests/fixtures/ui_theme_manifest_app.ai")
THEME_GOLDEN = Path("tests/fixtures/ui_theme_manifest_golden.json")
THEME_STATE = {
    "ui": {
        "settings": {
            "size": "normal",
            "radius": "lg",
        }
    }
}


def build_baseline_payloads() -> dict[Path, str]:
    payloads: dict[Path, str] = {}
    BASELINE_FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    for case in baseline_cases():
        snapshot = build_case_snapshot(case)
        path = BASELINE_FIXTURES_DIR / f"{case.name}.json"
        payloads[path] = canonical_json_dumps(snapshot, pretty=True)

    payloads[LAYOUT_GOLDEN] = canonical_json_dumps(_build_layout_manifest(), pretty=True)
    payloads[THEME_GOLDEN] = canonical_json_dumps(_build_theme_manifest(), pretty=True)
    return payloads


def write_baselines(payloads: dict[Path, str]) -> list[Path]:
    written: list[Path] = []
    for path in sorted(payloads, key=lambda p: p.as_posix()):
        content = payloads[path]
        existing = path.read_text(encoding="utf-8") if path.exists() else None
        if existing == content:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


def check_baselines(payloads: dict[Path, str]) -> list[Path]:
    missing_or_changed: list[Path] = []
    for path in sorted(payloads, key=lambda p: p.as_posix()):
        content = payloads[path]
        existing = path.read_text(encoding="utf-8") if path.exists() else None
        if existing != content:
            missing_or_changed.append(path)
    return missing_or_changed


def _lower_ir_program(source: str):
    if not _has_spec(source):
        source = 'spec is "1.0"\n\n' + source.lstrip("\n")
    return lower_program(parse(source))


def _build_layout_manifest() -> dict:
    program = _lower_ir_program(LAYOUT_FIXTURE.read_text(encoding="utf-8"))
    return build_manifest(program, state=dict(LAYOUT_STATE), store=None, mode=ValidationMode.STATIC)


def _build_theme_manifest() -> dict:
    program = _lower_ir_program(THEME_FIXTURE.read_text(encoding="utf-8"))
    return build_manifest(program, state=dict(THEME_STATE), store=None, mode=ValidationMode.STATIC)


def _has_spec(source: str) -> bool:
    for line in source.splitlines():
        if line.strip().startswith('spec is "'):
            return True
    return False


def _print_paths(label: str, paths: Iterable[Path]) -> None:
    entries = list(paths)
    if not entries:
        return
    print(label)
    for path in entries:
        print(f"  {path.as_posix()}")


def _main() -> int:
    parser = argparse.ArgumentParser(description="Refresh deterministic UI baselines.")
    parser.add_argument("--write", action="store_true", help="Write baseline fixtures to disk.")
    parser.add_argument("--check", action="store_true", help="Verify baseline fixtures without writing.")
    args = parser.parse_args()

    if not args.write and not args.check:
        args.check = True

    payloads = build_baseline_payloads()

    if args.check:
        missing_or_changed = check_baselines(payloads)
        if missing_or_changed:
            _print_paths("Baselines differ. Run with --write to refresh:", missing_or_changed)
            return 1
        print("Baselines are up to date.")
        return 0

    written = write_baselines(payloads)
    if written:
        _print_paths("Baselines refreshed:", written)
    else:
        print("Baselines already up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
