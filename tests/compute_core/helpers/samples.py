from __future__ import annotations

from pathlib import Path
from typing import Iterable


SAMPLES = [
    ("compute_core", Path("tests/compute_core/fixtures/compute_core.ai")),
]


def sample_sources() -> Iterable[tuple[str, Path, str]]:
    for name, path in SAMPLES:
        yield name, path, path.read_text(encoding="utf-8")


__all__ = ["SAMPLES", "sample_sources"]
