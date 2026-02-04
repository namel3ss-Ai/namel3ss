from namel3ss.ast import nodes as ast
from tests.conftest import parse_program


SOURCE = '''ai "assistant":
  model is "gpt-4.1"
  system_prompt is "You are helpful"

spec is "1.0"

flow "demo":
  ask ai "assistant" with input: "Hello" as reply
'''


def test_parse_ai_decl_and_ask_expression():
    program = parse_program(SOURCE)
    assert len(program.ais) == 1
    ai = program.ais[0]
    assert ai.name == "assistant"
    assert ai.model == "gpt-4.1"
    flow = program.flows[0]
    ask_stmt = flow.body[0]
    assert isinstance(ask_stmt, ast.AskAIStmt)
    assert ask_stmt.ai_name == "assistant"
    assert ask_stmt.target == "reply"
    assert ask_stmt.input_mode == "text"


def test_parse_ask_ai_structured_input():
    source = '''spec is "1.0"

ai "assistant":
  model is "gpt-4.1"

flow "demo":
  ask ai "assistant" with structured input from state.payload as reply
'''
    program = parse_program(source)
    ask_stmt = program.flows[0].body[0]
    assert isinstance(ask_stmt, ast.AskAIStmt)
    assert ask_stmt.input_mode == "structured"


def test_parse_ask_ai_input_without_colon():
    source = '''spec is "1.0"

ai "assistant":
  model is "gpt-4.1"

flow "demo":
  ask ai "assistant" with input "Hello" as reply
'''
    program = parse_program(source)
    ask_stmt = program.flows[0].body[0]
    assert isinstance(ask_stmt, ast.AskAIStmt)
    assert ask_stmt.input_mode == "text"
