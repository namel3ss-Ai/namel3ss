from __future__ import annotations

from pathlib import Path
from typing import Iterable


SAMPLES = [
    ("starter_template", Path("src/namel3ss/templates/starter/app.ai")),
    ("demo_template", Path("src/namel3ss/templates/demo/app.ai")),
    ("control_flow", Path("tests/spec_freeze/fixtures/control_flow.ai")),
]


def sample_sources() -> Iterable[tuple[str, Path, str]]:
    for name, path in SAMPLES:
        yield name, path, path.read_text(encoding="utf-8")


__all__ = ["SAMPLES", "sample_sources"]
