from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_parse_translate_qa_cot_and_chain_patterns() -> None:
    source = '''
translate "en_to_fr":
  model is "gpt-4"
  source_language is "en"
  target_language is "fr"
  prompt is "Translate: " + input.text
  output is text

qa "answer_question":
  model is "gpt-4"
  prompt is "Qn: " + input.question + "\\nCtx: " + input.context + "\\nAns: "
  output:
    ans is text
    confidence is number
  tests:
    dataset is "qa_examples.json"
    metrics:
      - accuracy
      - exact_match

cot "reason_step_by_step":
  model is "gpt-4"
  prompt is "Solve step by step: " + input.problem
  output:
    reasoning is text
    ans is text

chain "summarise_and_classify":
  steps:
    - call summarise "summarise_doc" with input.document
    - call classification "classify_summary" with summarise_doc.result
  output:
    sentiment is text
'''.lstrip()
    program = parse_program(source)
    kinds = {flow.name: flow.kind for flow in program.ai_flows}
    assert kinds["en_to_fr"] == "translate"
    assert kinds["answer_question"] == "qa"
    assert kinds["reason_step_by_step"] == "cot"
    assert kinds["summarise_and_classify"] == "chain"

    translate = next(flow for flow in program.ai_flows if flow.name == "en_to_fr")
    assert translate.prompt is None
    assert translate.prompt_expr is not None
    assert translate.source_language == "en"
    assert translate.target_language == "fr"

    qa = next(flow for flow in program.ai_flows if flow.name == "answer_question")
    assert qa.tests is not None
    assert qa.tests.dataset == "qa_examples.json"
    assert qa.tests.metrics == ["accuracy", "exact_match"]
    assert [field.name for field in qa.output_fields or []] == ["ans", "confidence"]

    chain = next(flow for flow in program.ai_flows if flow.name == "summarise_and_classify")
    assert chain.chain_steps is not None
    assert [step.flow_name for step in chain.chain_steps] == ["summarise_doc", "classify_summary"]
    assert [field.name for field in chain.output_fields or []] == ["sentiment"]


def test_chain_missing_steps_errors() -> None:
    source = '''
chain "invalid_chain":
  output:
    result is text
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert exc.value.message == "Chain flow is missing steps"
