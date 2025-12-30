from __future__ import annotations

from pathlib import Path
from typing import Iterable


SAMPLES = [
    ("demo_crud_dashboard", Path("examples/demo_crud_dashboard.ai")),
    ("demo_multi_agent_orchestration", Path("examples/demo_multi_agent_orchestration.ai")),
    ("control_flow", Path("tests/spec_freeze/fixtures/control_flow.ai")),
]


def sample_sources() -> Iterable[tuple[str, Path, str]]:
    for name, path in SAMPLES:
        yield name, path, path.read_text(encoding="utf-8")


__all__ = ["SAMPLES", "sample_sources"]
