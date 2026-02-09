from namel3ss.determinism import canonical_json_dumps
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


SOURCE = '''capabilities:
  ui_rag

flow "answer_question":
  return "ok"

page "RAG":
  rag_ui:
    features: conversation, evidence
    binds:
      messages from is state.chat.messages
      on_send calls flow "answer_question"
      citations from is state.chat.citations
      trust when is state.chat.trust
      source_preview from is state.chat.preview
      thinking when is state.loading
'''

STATE = {
    "chat": {
        "messages": [
            {
                "role": "assistant",
                "content": "Grounded answer",
                "streaming": True,
                "tokens": ["Grounded", " ", "answer"],
                "trust": 0.88,
            }
        ],
        "citations": [
            {"title": "Policy", "source_id": "doc-policy", "snippet": "Policy excerpt", "page_number": 3},
            {"title": "Handbook", "source_id": "doc-handbook", "snippet": "Handbook excerpt", "page_number": 8},
        ],
        "trust": 0.88,
        "preview": {
            "title": "Policy",
            "source_id": "doc-policy",
            "snippet": "Policy excerpt",
            "document_id": "doc-policy",
            "page_number": 3,
        },
    },
    "loading": False,
    "ui": {"show_drawer": True},
}


def test_rag_chat_manifest_determinism() -> None:
    program = lower_ir_program(SOURCE)
    first = build_manifest(program, state=dict(STATE), store=None)
    second = build_manifest(program, state=dict(STATE), store=None)
    assert canonical_json_dumps(first, pretty=False) == canonical_json_dumps(second, pretty=False)
