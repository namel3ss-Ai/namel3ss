from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_parse_prompt_declaration() -> None:
    source = '''
prompt "summary_prompt":
  version is "1.0.0"
  text is "Summarise the input."
  description is "Short summary."
'''.lstrip()
    program = parse_program(source)
    assert len(program.prompts) == 1
    prompt = program.prompts[0]
    assert prompt.name == "summary_prompt"
    assert prompt.version == "1.0.0"
    assert prompt.text == "Summarise the input."
    assert prompt.description == "Short summary."


def test_prompt_missing_version_errors() -> None:
    source = '''
prompt "summary_prompt":
  text is "Summarise the input."
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert exc.value.message == "Prompt is missing a version"
