import json
from pathlib import Path

from namel3ss.runtime.execution.builder import build_execution_graph
from namel3ss.runtime.execution.render_plain import render_how

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_match_reports_skipped_cases() -> None:
    pack = _load_fixture("last_002.json")
    text = render_how(build_execution_graph(pack))
    assert "case 1 skipped" in text


def test_repeat_and_for_each_report_skips() -> None:
    pack = _load_fixture("last_003.json")
    text = render_how(build_execution_graph(pack))
    assert "skipped repeat body" in text
    assert "skipped for each body" in text
