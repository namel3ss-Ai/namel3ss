import json
from pathlib import Path

from namel3ss.runtime.tools.explain.collector import collect_tool_decisions

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_collect_decisions_from_tool_traces() -> None:
    execution_last = _load_fixture("execution_last.json")
    run_last = _load_fixture("run_last.json")
    decisions = collect_tool_decisions(execution_last=execution_last, run_payload=run_last)
    assert len(decisions) == 1
    decision = decisions[0]
    assert decision.tool_name == "greet someone"
    assert decision.status == "blocked"
    assert decision.permission.allowed is False
    assert any("guarantee_blocked" in reason for reason in decision.permission.reasons)
