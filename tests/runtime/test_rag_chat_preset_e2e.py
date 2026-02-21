from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

from namel3ss.runtime.backend.upload_handler import handle_upload
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.runtime.ui.actions import handle_action
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


SOURCE = '''spec is "1.0"
use preset "rag_chat":
  title is "Assistant"

override flow "rag.answer":
  set state.test_observed with:
    message is input.message
    context is input.context
  return input.message
'''

SOURCE_CONTEXT_ECHO = '''spec is "1.0"
use preset "rag_chat":
  title is "Assistant"

override flow "rag.answer":
  return input.context
'''

SOURCE_TEMPLATE = '''spec is "1.0"
use preset "rag_chat":
  title is "Assistant"
  model is "gpt-4o-mini"
  answer_template is "summary_keypoints_recommendation_with_citations"
'''

NO_SUPPORT = "No grounded support found in indexed sources for this query."
PROVIDER_FALLBACK = (
    "Summary:\n"
    "Grounded evidence was found for this question [1]. AI synthesis is currently unavailable in this runtime [1].\n\n"
    "Key Points:\n"
    "1. The indexed context contains supporting information [1].\n"
    "2. View Sources remains available for direct evidence review [1].\n"
    "3. Provider credentials are required for synthesized answers [1].\n\n"
    "Recommendation:\n"
    "Set NAMEL3SS_OPENAI_API_KEY, rerun the app, and ask again for a fully composed response [1]."
)


def test_rag_chat_preset_chat_send_receives_message_and_retrieval_context() -> None:
    program = lower_ir_program(SOURCE)
    state = _seed_state_with_retrieval_data()
    action_id = _rag_answer_action_id(program, state=state)
    response = handle_action(
        program,
        action_id=action_id,
        payload={"message": "alpha"},
        state=state,
        store=MemoryStore(),
    )
    observed = response["state"]["test_observed"]
    assert observed["message"] == "alpha"
    context = observed["context"]
    assert isinstance(context, str)
    assert context.strip() != ""
    assert "alpha context from doc" in context
    citations = response["state"]["chat"]["citations"]
    assert isinstance(citations, list)
    assert citations
    messages = response["state"]["chat"]["messages"]
    assert isinstance(messages, list)
    assert len(messages) == 2
    assistant = messages[1]
    assistant_citations = assistant.get("citations")
    assert isinstance(assistant_citations, list)
    assert assistant_citations
    assert assistant_citations == citations


def test_rag_chat_preset_returns_no_support_message_when_retrieval_is_empty() -> None:
    program = lower_ir_program(SOURCE)
    state: dict = {}
    action_id = _rag_answer_action_id(program, state=state)
    response = handle_action(
        program,
        action_id=action_id,
        payload={"message": "beta"},
        state=state,
        store=MemoryStore(),
    )
    messages = response["state"]["chat"]["messages"]
    assert isinstance(messages, list)
    assert len(messages) == 2
    assistant = messages[1]
    assert assistant["role"] == "assistant"
    assert assistant["content"] == "No grounded support found in indexed sources for this query."


def test_rag_chat_preset_accepts_chat_upload_map_state_shape() -> None:
    program = lower_ir_program(SOURCE)
    state = {
        "uploads": {
            "chat_files": {
                "upload-1": {
                    "id": "",
                    "name": "doc.txt",
                }
            }
        }
    }
    action_id = _rag_answer_action_id(program, state=state)
    response = handle_action(
        program,
        action_id=action_id,
        payload={"message": "beta"},
        state=state,
        store=MemoryStore(),
    )
    messages = response["state"]["chat"]["messages"]
    assert isinstance(messages, list)
    assert len(messages) == 2
    assert (
        messages[1]["content"]
        == "Scope: attached files\nNo grounded support found in indexed sources for this query."
    )
    assert response["state"]["uploads"]["chat_files"] == []


def test_rag_chat_preset_keeps_attachment_scope_when_query_has_no_match() -> None:
    program = lower_ir_program(SOURCE)
    state = _seed_state_with_retrieval_data()
    state["uploads"] = {
        "chat_files": {
            "upload-1": {
                "id": "",
                "name": "doc.txt",
                "type": "text/plain",
            }
        }
    }
    action_id = _rag_answer_action_id(program, state=state)
    response = handle_action(
        program,
        action_id=action_id,
        payload={"message": "zebra quasar helium"},
        state=state,
        store=MemoryStore(),
    )
    messages = response["state"]["chat"]["messages"]
    assert isinstance(messages, list)
    assert len(messages) == 2
    assert (
        messages[1]["content"]
        == "Scope: attached files\nNo grounded support found in indexed sources for this query."
    )
    assert response["state"]["uploads"]["chat_files"] == []


def test_rag_chat_preset_pdf_with_indexed_chunks_falls_back_to_attached_context(tmp_path: Path) -> None:
    program = lower_ir_program(SOURCE)
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    program.project_root = str(tmp_path)
    program.app_path = app_path.as_posix()

    metadata = _upload_pdf_metadata(
        tmp_path,
        _minimal_text_pdf_bytes(
            "alpha context from pdf with enough readable words to pass quality gating and support deterministic indexing behavior in tests"
        ),
        filename="doc.pdf",
    )
    upload_id = str(metadata["checksum"])
    state = {
        "uploads": {
            "chat_files": {
                upload_id: {
                    "id": upload_id,
                    "name": str(metadata["name"]),
                    "type": "application/pdf",
                    "checksum": upload_id,
                }
            }
        }
    }
    action_id = _rag_answer_action_id(program, state=state)
    response = handle_action(
        program,
        action_id=action_id,
        payload={"message": "zebra quasar helium"},
        state=state,
        store=MemoryStore(),
    )
    messages = response["state"]["chat"]["messages"]
    assert isinstance(messages, list)
    assert len(messages) == 2
    assert (
        messages[1]["content"].startswith("Scope: attached files\nzebra quasar helium")
    )
    observed = response["state"]["test_observed"]
    assert isinstance(observed["context"], str)
    assert "alpha context from pdf" in observed["context"]
    citations = response["state"]["chat"]["citations"]
    assert isinstance(citations, list)
    assert len(citations) == 1
    citation = citations[0]
    assert citation["source_id"] == upload_id
    assert citation["document_id"] == upload_id
    assert citation["page_number"] == 1
    assert isinstance(citation["preview_url"], str)
    assert f"/api/documents/{upload_id}/pages/1" in citation["preview_url"]
    assistant = messages[1]
    assistant_citations = assistant.get("citations")
    assert isinstance(assistant_citations, list)
    assert len(assistant_citations) == 1


def test_rag_chat_preset_attachment_scope_preserves_override_context_response() -> None:
    program = lower_ir_program(SOURCE_CONTEXT_ECHO)
    state = _seed_state_with_retrieval_data()
    state["uploads"] = {
        "chat_files": {
            "doc-1": {
                "id": "",
                "name": "doc-1.txt",
                "type": "text/plain",
                "checksum": "",
            }
        }
    }
    action_id = _rag_answer_action_id(program, state=state)
    response = handle_action(
        program,
        action_id=action_id,
        payload={"message": "alpha"},
        state=state,
        store=MemoryStore(),
    )
    messages = response["state"]["chat"]["messages"]
    assert isinstance(messages, list)
    assert len(messages) == 2
    assert (
        messages[1]["content"].startswith("Scope: attached files\n[1] alpha context from doc")
    )
    assistant_citations = messages[1].get("citations")
    assert isinstance(assistant_citations, list)
    assert len(assistant_citations) == 1
    assert assistant_citations[0]["source_id"] == "doc-1"


def test_rag_chat_preset_uses_pdf_fallback_message_when_pdf_has_no_context() -> None:
    program = lower_ir_program(SOURCE)
    state = {
        "uploads": {
            "chat_files": {
                "upload-1": {
                    "id": "",
                    "name": "doc.pdf",
                    "type": "application/pdf",
                }
            }
        }
    }
    action_id = _rag_answer_action_id(program, state=state)
    response = handle_action(
        program,
        action_id=action_id,
        payload={"message": "beta"},
        state=state,
        store=MemoryStore(),
    )
    messages = response["state"]["chat"]["messages"]
    assert isinstance(messages, list)
    assert len(messages) == 2
    assert (
        messages[1]["content"]
        == "Scope: attached files\nI could not extract readable text from the selected PDF source. Upload a text-searchable PDF (or OCR text), wait for indexing to finish, then ask again."
    )
    assert response["state"]["uploads"]["chat_files"] == []


def test_rag_chat_template_returns_no_support_message_when_context_is_empty(monkeypatch) -> None:
    monkeypatch.delenv("NAMEL3SS_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    program = lower_ir_program(SOURCE_TEMPLATE)
    state: dict = {}
    action_id = _rag_answer_action_id(program, state=state)
    response = handle_action(
        program,
        action_id=action_id,
        payload={"message": "what is this about"},
        state=state,
        store=MemoryStore(),
    )
    messages = response["state"]["chat"]["messages"]
    assert isinstance(messages, list)
    assert len(messages) == 2
    assert messages[1]["content"] == NO_SUPPORT


def test_rag_chat_template_returns_provider_fallback_when_context_exists_and_ai_fails(monkeypatch) -> None:
    monkeypatch.delenv("NAMEL3SS_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    program = lower_ir_program(SOURCE_TEMPLATE)
    state = _seed_state_with_retrieval_data()
    action_id = _rag_answer_action_id(program, state=state)
    response = handle_action(
        program,
        action_id=action_id,
        payload={"message": "alpha"},
        state=state,
        store=MemoryStore(),
    )
    messages = response["state"]["chat"]["messages"]
    assert isinstance(messages, list)
    assert len(messages) == 2
    assert messages[1]["content"] == PROVIDER_FALLBACK


def _rag_answer_action_id(program, *, state: dict) -> str:
    manifest = build_manifest(program, state=state, store=MemoryStore())
    for action_id, entry in manifest.get("actions", {}).items():
        if entry.get("type") == "call_flow" and entry.get("flow") == "rag.answer":
            return action_id
    raise AssertionError("rag.answer action not found")


def _seed_state_with_retrieval_data() -> dict:
    return {
        "ingestion": {
            "doc-1": {"status": "pass"},
        },
        "index": {
            "chunks": [
                {
                    "upload_id": "doc-1",
                    "chunk_id": "doc-1:0",
                    "document_id": "doc-1",
                    "source_name": "doc-1.txt",
                    "page_number": 1,
                    "chunk_index": 0,
                    "ingestion_phase": "deep",
                    "keywords": ["alpha", "context"],
                    "text": "alpha context from doc",
                }
            ]
        },
    }


def _upload_pdf_metadata(tmp_path: Path, payload: bytes, *, filename: str) -> dict:
    app_path = tmp_path / "app.ai"
    ctx = SimpleNamespace(
        capabilities=("uploads",),
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
    )
    response = handle_upload(
        ctx,
        headers={"Content-Type": "application/pdf"},
        rfile=io.BytesIO(payload),
        content_length=len(payload),
        upload_name=filename,
    )
    return response["upload"]


def _minimal_text_pdf_bytes(text: str) -> bytes:
    body = (
        "%PDF-1.4\n"
        "1 0 obj\n"
        "<< /Type /Catalog /Pages 2 0 R >>\n"
        "endobj\n"
        "2 0 obj\n"
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
        "endobj\n"
        "3 0 obj\n"
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Contents 4 0 R >>\n"
        "endobj\n"
        "4 0 obj\n"
        "<< /Length 64 >>\n"
        "stream\n"
        "BT\n"
        "/F1 12 Tf\n"
        "72 720 Td\n"
        f"({text}) Tj\n"
        "ET\n"
        "endstream\n"
        "endobj\n"
        "trailer\n"
        "<< /Root 1 0 R >>\n"
        "%%EOF\n"
    )
    return body.encode("utf-8")
