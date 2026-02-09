from namel3ss.determinism import canonical_json_dumps
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


SOURCE = '''capabilities:
  ui_rag

flow "answer_question":
  return "ok"

page "RAG":
  rag_ui:
    binds:
      messages from is state.chat.messages
      on_send calls flow "answer_question"
      citations from is state.chat.citations
'''

STATE = {
    "chat": {"messages": [], "citations": []},
    "ui": {"show_drawer": False},
    "loading": False,
}


def test_rag_ui_manifest_determinism() -> None:
    program = lower_ir_program(SOURCE)
    first = build_manifest(program, state=dict(STATE), store=None)
    second = build_manifest(program, state=dict(STATE), store=None)
    assert canonical_json_dumps(first, pretty=False) == canonical_json_dumps(second, pretty=False)
