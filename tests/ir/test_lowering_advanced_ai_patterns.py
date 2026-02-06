from __future__ import annotations

from tests.conftest import lower_ir_program


def test_lower_qa_and_chain_pattern_metadata() -> None:
    source = '''
qa "answer_question":
  model is "gpt-4"
  prompt is "Qn: " + input.question + "\\nCtx: " + input.context + "\\nAns: "
  output:
    ans is text
  tests:
    dataset is "qa_examples.json"
    metrics:
      - accuracy

chain "qa_chain":
  steps:
    - call qa "answer_question" with input
  output:
    ans is text
'''.lstrip()
    program = lower_ir_program(source)

    qa = next(flow for flow in program.ai_flows if flow.name == "answer_question")
    assert qa.kind == "qa"
    assert qa.prompt_expr is not None
    assert qa.tests is not None
    assert qa.tests.metrics == ["accuracy"]

    chain = next(flow for flow in program.ai_flows if flow.name == "qa_chain")
    assert chain.kind == "chain"
    assert chain.chain_steps is not None
    assert chain.chain_steps[0].flow_name == "answer_question"

    flow = next(item for item in program.flows if item.name == "qa_chain")
    assert flow.ai_metadata is not None
    assert flow.ai_metadata.kind == "chain"
    assert flow.ai_metadata.chain_steps is not None
