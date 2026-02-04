from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


SOURCE = '''contract flow "answer":
  input:
    question is text
  output:
    result is text

flow "answer":
  return "ok"

page "home":
  input text as question
    send to flow "answer"
'''


def test_input_manifest_includes_action():
    program = lower_ir_program(SOURCE)
    manifest = build_manifest(program, state={})
    element = manifest["pages"][0]["elements"][0]
    assert element["type"] == "input"
    assert element["name"] == "question"
    assert element["action"]["input_field"] == "question"
    action_id = element["action_id"]
    assert action_id in manifest["actions"]
    action = manifest["actions"][action_id]
    assert action["type"] == "call_flow"
    assert action["flow"] == "answer"
    assert action["input_field"] == "question"
    assert action["input_type"] == "text"


def test_input_manifest_is_deterministic():
    program = lower_ir_program(SOURCE)
    first = build_manifest(program, state={})
    second = build_manifest(program, state={})
    assert first == second
