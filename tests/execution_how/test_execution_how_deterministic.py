import json
from pathlib import Path

from namel3ss.runtime.execution.builder import build_execution_graph
from namel3ss.runtime.execution.render_plain import render_how

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_how_is_deterministic() -> None:
    pack = _load_fixture("last_001.json")
    text_one = render_how(build_execution_graph(pack))
    text_two = render_how(build_execution_graph(pack))
    assert text_one == text_two


def test_how_includes_branch_taken_and_skipped() -> None:
    pack = _load_fixture("last_001.json")
    text = render_how(build_execution_graph(pack))
    assert "took then branch" in text
    assert "skipped else branch" in text
