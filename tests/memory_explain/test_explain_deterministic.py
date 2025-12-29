import json
from pathlib import Path

from namel3ss.runtime.memory.explain.builder import build_graph
from namel3ss.runtime.memory.explain.normalize import normalize_graph
from namel3ss.runtime.memory.explain.render_plain import render_why

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_explain_is_deterministic() -> None:
    pack = _load_fixture("last_001.json")
    text_one = render_why(normalize_graph(build_graph(pack)))
    text_two = render_why(normalize_graph(build_graph(pack)))
    assert text_one == text_two


def test_explain_mentions_counts_and_phase() -> None:
    pack = _load_fixture("last_001.json")
    text = render_why(normalize_graph(build_graph(pack)))
    assert "Recalled 2 items" in text
    assert "short_term" in text
    assert "Phase:" in text
