from __future__ import annotations

from urllib.parse import quote

from namel3ss.config.model import AppConfig
from namel3ss.rag.determinism import stable_preview_query
from namel3ss.rag.ingestion import run_ingestion_pipeline
from namel3ss.rag.retrieval import (
    build_chat_prompt,
    build_preview_routes,
    run_chat_answer_service,
    run_retrieval_service,
)
from namel3ss.runtime.ai.provider import AIProvider, AIResponse


class StaticProvider(AIProvider):
    def __init__(self, output: str) -> None:
        self.output = output

    def ask(
        self,
        *,
        model: str,
        system_prompt: str | None,
        user_input: str,
        tools=None,
        memory=None,
        tool_results=None,
    ) -> AIResponse:
        return AIResponse(output=self.output)


def test_phase1_ingestion_to_answer_pipeline_is_end_to_end() -> None:
    state: dict = {}
    run_ingestion_pipeline(
        state=state,
        content=b"Alpha policy clause.\n\nBeta payment clause.\n\nGamma appendix.",
        source_name="policy.txt",
        source_identity="fixtures/policy.txt",
        source_type="upload",
        source_uri="upload://fixtures/policy.txt",
        mime_type="text/plain",
    )
    chunks = state.get("index", {}).get("chunks", [])
    assert chunks
    first_chunk_id = str(chunks[0].get("chunk_id"))
    answer = run_chat_answer_service(
        query="alpha",
        state=state,
        project_root=None,
        app_path=None,
        provider=StaticProvider(f"Alpha policy clause. [{first_chunk_id}]"),
        provider_name="test",
        config=AppConfig(),
    )
    assert answer["answer_text"] == f"Alpha policy clause. [{first_chunk_id}]"
    citations = answer["citations"]
    assert len(citations) == 1
    assert citations[0]["chunk_id"] == first_chunk_id
    assert citations[0]["doc_id"] == str(chunks[0].get("document_id"))
    assert citations[0]["page_number"] == int(chunks[0].get("page_number"))


def test_phase1_retrieval_repeatability_on_fixture_corpus() -> None:
    state: dict = {}
    run_ingestion_pipeline(
        state=state,
        content=b"Alpha operations checklist.\n\nRelease gating policy.",
        source_name="ops.txt",
        source_identity="fixtures/ops.txt",
        source_type="upload",
        source_uri="upload://fixtures/ops.txt",
        mime_type="text/plain",
    )
    run_ingestion_pipeline(
        state=state,
        content=b"Alpha customer runbook.\n\nEscalation matrix and ownership.",
        source_name="runbook.txt",
        source_identity="fixtures/runbook.txt",
        source_type="upload",
        source_uri="upload://fixtures/runbook.txt",
        mime_type="text/plain",
    )
    retrieval_config = {
        "top_k": 4,
        "filters": {"tags": []},
        "scope": {"collections": [], "documents": []},
    }
    first = run_retrieval_service(
        query="alpha",
        state=state,
        project_root=None,
        app_path=None,
        retrieval_config=retrieval_config,
    )
    second = run_retrieval_service(
        query="alpha",
        state=state,
        project_root=None,
        app_path=None,
        retrieval_config=retrieval_config,
    )
    assert first == second
    result_rows = first["retrieval_results"]
    assert result_rows
    assert [row["rank"] for row in result_rows] == list(range(1, len(result_rows) + 1))


def test_phase1_prompt_builder_snapshot_is_stable() -> None:
    retrieval_rows = [
        {
            "chunk_id": "doc-a:0",
            "chunk_index": 0,
            "document_id": "doc-a",
            "ingestion_phase": "deep",
            "page_number": 1,
            "source_name": "alpha.txt",
            "text": "Alpha policy clause.",
        },
        {
            "chunk_id": "doc-b:2",
            "chunk_index": 2,
            "document_id": "doc-b",
            "ingestion_phase": "deep",
            "page_number": 2,
            "source_name": "beta.txt",
            "text": "Beta implementation detail.",
        },
    ]
    first = build_chat_prompt(query=" What changed? ", retrieval_rows=list(reversed(retrieval_rows)))
    second = build_chat_prompt(query=" What changed? ", retrieval_rows=list(reversed(retrieval_rows)))
    assert first == second
    assert first["source_count"] == 2
    assert first["prompt_hash"] == "4801938a78914b83e2f845374091855db64619c96f05ce1ddb12132cca64ab3c"


def test_phase1_basic_preview_page_jump_snapshot_is_stable() -> None:
    state: dict = {}
    run_ingestion_pipeline(
        state=state,
        content=b"Alpha policy clause.\n\nBeta payment clause.",
        source_name="policy.txt",
        source_identity="fixtures/preview-policy.txt",
        source_type="upload",
        source_uri="upload://fixtures/preview-policy.txt",
        mime_type="text/plain",
    )
    chunks = state.get("index", {}).get("chunks", [])
    assert chunks
    first_chunk_id = str(chunks[0].get("chunk_id"))
    answer = run_chat_answer_service(
        query="alpha",
        state=state,
        project_root=None,
        app_path=None,
        provider=StaticProvider(f"Alpha policy clause. [{first_chunk_id}]"),
        provider_name="test",
        config=AppConfig(),
    )
    snippet_map = {
        str(chunk.get("chunk_id")): str(chunk.get("text") or "")
        for chunk in chunks
        if isinstance(chunk, dict)
    }
    first = build_preview_routes(citations=answer["citations"], snippet_by_chunk=snippet_map)
    second = build_preview_routes(citations=answer["citations"], snippet_by_chunk=snippet_map)
    assert first == second
    assert len(first) == 1
    route = first[0]
    citation = answer["citations"][0]
    doc_id = str(citation.get("doc_id"))
    page_number = int(citation.get("page_number"))
    chunk_id = str(citation.get("chunk_id"))
    citation_id = str(citation.get("citation_id"))
    assert route["preview_url"] == (
        f"/api/documents/{quote(doc_id, safe='')}/pages/{page_number}?chunk_id={quote(chunk_id, safe='')}"
    )
    assert route["deep_link_query"] == stable_preview_query(
        doc_id=doc_id,
        page_number=page_number,
        citation_id=citation_id,
    )
