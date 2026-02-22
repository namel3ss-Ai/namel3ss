from __future__ import annotations

from pathlib import Path

from tests.conftest import run_flow


STARTER_PATH = Path("tests/fixtures/agent_workspace/starter.ai")
CONTROLLED_PATH = Path("tests/fixtures/agent_workspace/controlled.ai")
FULL_CUSTOM_PATH = Path("tests/fixtures/agent_workspace/full_custom.ai")


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def test_agent_tier_example_line_count_gates() -> None:
    assert _line_count(STARTER_PATH) <= 10
    assert 30 <= _line_count(CONTROLLED_PATH) <= 90
    assert _line_count(FULL_CUSTOM_PATH) >= 100


def test_agent_tier_examples_execute_and_preserve_expected_behavior() -> None:
    starter = run_flow(
        STARTER_PATH.read_text(encoding="utf-8"),
        flow_name="agent.answer",
        input_data={"message": "What is this?", "context": ""},
    )
    assert starter.last_value == {
        "answer_text": "No grounded support found in indexed sources for this query.",
        "citations": [],
    }

    controlled = run_flow(
        CONTROLLED_PATH.read_text(encoding="utf-8"),
        flow_name="agent.answer",
        input_data={"message": "What is this?", "context": ""},
    )
    assert controlled.last_value == {
        "answer_text": "Controlled fallback: What is this?",
        "citations": [],
    }

    full_custom_source = FULL_CUSTOM_PATH.read_text(encoding="utf-8")
    assert "use preset" not in full_custom_source
    full_custom = run_flow(
        full_custom_source,
        flow_name="agent.answer",
        input_data={"message": "What is this?", "context": ""},
    )
    assert full_custom.last_value == {
        "answer_text": "No grounded support found in indexed sources for this query.",
        "citations": [],
    }
