from namel3ss.parser.core import parse


def test_ai_provider_parses():
    program = parse(
        '''ai "assistant":
  provider is "ollama"
  model is "llama3.1"
'''
    )
    assert program.ais[0].provider == "ollama"
    assert program.ais[0].model == "llama3.1"


def test_ai_provider_defaults_none_in_ast():
    program = parse(
        '''ai "assistant":
  model is "gpt-4.1"
'''
    )
    assert program.ais[0].provider is None
