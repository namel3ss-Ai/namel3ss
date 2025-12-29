import json
from pathlib import Path

from namel3ss.runtime.memory.explain.builder import build_graph
from namel3ss.runtime.memory.explain.normalize import normalize_graph
from namel3ss.runtime.memory.explain.render_plain import render_why

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_why_not_default_message() -> None:
    pack = _load_fixture("last_001.json")
    text = render_why(normalize_graph(build_graph(pack)))
    assert "No explicit skip reasons were recorded for this run." in text


def test_why_not_reports_skips() -> None:
    pack = _load_fixture("last_002.json")
    text = render_why(normalize_graph(build_graph(pack)))
    assert "No explicit skip reasons were recorded for this run." not in text
    assert "disabled" in text
    assert "governance" in text
