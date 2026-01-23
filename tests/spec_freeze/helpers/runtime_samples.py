from __future__ import annotations

from pathlib import Path
from typing import Iterable


RUNTIME_SAMPLES = [
    ("starter_seed_note", Path("tests/fixtures/templates/starter_template.ai"), "seed_note"),
    ("runtime_control", Path("tests/spec_freeze/fixtures/runtime_control.ai"), "control"),
    ("runtime_theme", Path("tests/spec_freeze/fixtures/runtime_theme.ai"), "theme_demo"),
]


def runtime_sources() -> Iterable[tuple[str, Path, str, str]]:
    for name, path, flow in RUNTIME_SAMPLES:
        yield name, path, flow, path.read_text(encoding="utf-8")


__all__ = ["RUNTIME_SAMPLES", "runtime_sources"]
