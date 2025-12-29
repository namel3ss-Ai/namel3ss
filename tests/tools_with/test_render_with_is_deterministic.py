import json
from pathlib import Path

from namel3ss.runtime.tools.explain.builder import build_tool_explain_pack
from namel3ss.runtime.tools.explain.decision import ToolDecision
from namel3ss.runtime.tools.explain.render_plain import render_with

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_render_with_is_deterministic() -> None:
    execution_last = _load_fixture("execution_last.json")
    run_last = _load_fixture("run_last.json")
    pack = build_tool_explain_pack(execution_last, run_last)
    decisions = [ToolDecision.from_dict(item) for item in pack.get("decisions", [])]
    text_one = render_with(decisions)
    text_two = render_with(decisions)
    assert text_one == text_two
