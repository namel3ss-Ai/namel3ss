import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
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
    assert ask_stmt.stream is False


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


def test_parse_ask_ai_image_input_mode():
    source = '''spec is "1.0"

ai "assistant":
  model is "gpt-4.1"

flow "demo":
  ask ai "assistant" with image input: "state.image_file" as reply
'''
    program = parse_program(source)
    ask_stmt = program.flows[0].body[0]
    assert isinstance(ask_stmt, ast.AskAIStmt)
    assert ask_stmt.input_mode == "image"


def test_parse_ask_ai_audio_input_mode():
    source = '''spec is "1.0"

ai "assistant":
  model is "gpt-4.1"

flow "demo":
  ask ai "assistant" with audio input: "state.audio_file" as reply
'''
    program = parse_program(source)
    ask_stmt = program.flows[0].body[0]
    assert isinstance(ask_stmt, ast.AskAIStmt)
    assert ask_stmt.input_mode == "audio"


def test_parse_ask_ai_with_stream_true():
    source = '''spec is "1.0"

ai "assistant":
  model is "gpt-4.1"

flow "demo":
  ask ai "assistant" with stream: true and input: "Hello" as reply
'''
    program = parse_program(source)
    ask_stmt = program.flows[0].body[0]
    assert isinstance(ask_stmt, ast.AskAIStmt)
    assert ask_stmt.stream is True
    assert ask_stmt.input_mode == "text"


def test_parse_ask_ai_with_stream_false():
    source = '''spec is "1.0"

ai "assistant":
  model is "gpt-4.1"

flow "demo":
  ask ai "assistant" with stream: false and input: "Hello" as reply
'''
    program = parse_program(source)
    ask_stmt = program.flows[0].body[0]
    assert isinstance(ask_stmt, ast.AskAIStmt)
    assert ask_stmt.stream is False


def test_parse_ask_ai_rejects_non_boolean_stream_value():
    source = '''spec is "1.0"

ai "assistant":
  model is "gpt-4.1"

flow "demo":
  ask ai "assistant" with stream: "yes" and input: "Hello" as reply
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "Expected true or false after 'stream'" in exc.value.message
