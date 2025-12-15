import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program


def test_old_ask_ai_expression_is_rejected():
    source = '''ai "assistant":
  model is "gpt-4.1"

flow "demo":
  let reply is ask ai "assistant" with input: "Hello"
  return reply
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "ai calls are statements" in str(exc.value).lower()
