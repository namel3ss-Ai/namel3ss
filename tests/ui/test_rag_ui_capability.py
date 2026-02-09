import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program


SOURCE = '''flow "answer_question":
  return "ok"

page "RAG":
  rag_ui:
    binds:
      messages from is state.chat.messages
      on_send calls flow "answer_question"
      citations from is state.chat.citations
'''


def test_rag_ui_requires_capability() -> None:
    with pytest.raises(Namel3ssError) as err:
        lower_ir_program(SOURCE)
    assert "rag_ui requires capability ui_rag" in str(err.value)
