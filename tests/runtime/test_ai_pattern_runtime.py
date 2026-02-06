from __future__ import annotations

from tests.conftest import run_flow


def test_qa_pattern_runs_with_dynamic_prompt_expression() -> None:
    source = '''
qa "answer_question":
  model is "gpt-4"
  prompt is "Qn: " + input.question + "\\nCtx: " + input.context + "\\nAns: "
  output:
    ans is text
'''.lstrip()
    result = run_flow(
        source,
        flow_name="answer_question",
        input_data={"question": "Hi", "context": "World"},
    )
    assert isinstance(result.last_value, dict)
    assert "ans" in result.last_value
    assert str(result.last_value["ans"]).startswith("[gpt-4] Qn: Hi")


def test_chain_pattern_runs_steps_in_order() -> None:
    source = '''
qa "answer_question":
  model is "gpt-4"
  prompt is "Qn: " + input.question + "\\nCtx: " + input.context + "\\nAns: "
  output:
    ans is text

chain "qa_chain":
  steps:
    - call qa "answer_question" with input
  output:
    ans is text
'''.lstrip()
    result = run_flow(
        source,
        flow_name="qa_chain",
        input_data={"question": "Hi", "context": "World"},
    )
    assert isinstance(result.last_value, dict)
    assert str(result.last_value.get("ans", "")).startswith("[gpt-4] Qn: Hi")
