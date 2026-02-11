from __future__ import annotations

from namel3ss.runtime.retrieval.trace_contract import TRACE_TIE_BREAKER, build_retrieval_trace_contract


def _results() -> list[dict]:
    return [
        {
            "chunk_id": "doc-b:0",
            "document_id": "doc-b",
            "upload_id": "doc-b",
            "source_name": "Doc B",
            "semantic_score": 0.8,
            "keyword_overlap": 4,
            "tags": ["support", "billing", "support"],
        },
        {
            "chunk_id": "doc-a:0",
            "document_id": "doc-a",
            "upload_id": "doc-a",
            "source_name": "Doc A",
            "semantic_score": 0.8,
            "keyword_overlap": 4,
            "tags": ["billing"],
        },
        {
            "chunk_id": "doc-c:0",
            "document_id": "doc-c",
            "upload_id": "doc-c",
            "source_name": "Doc C",
            "semantic_score": 0.2,
            "keyword_overlap": 1,
            "tags": ["ops"],
        },
    ]


def test_retrieval_trace_contract_is_deterministic_and_sorted() -> None:
    tuning = {
        "semantic_weight": 0.5,
        "semantic_k": 10,
        "lexical_k": 10,
        "final_top_k": 10,
    }

    first = build_retrieval_trace_contract(
        query="alpha",
        tuning=tuning,
        filter_tags=["support", "billing", "support"],
        results=_results(),
        vector_scores=None,
    )
    second = build_retrieval_trace_contract(
        query="alpha",
        tuning=tuning,
        filter_tags=["support", "billing", "support"],
        results=_results(),
        vector_scores=None,
    )

    assert first == second
    assert first["tie_breaker"] == TRACE_TIE_BREAKER
    assert first["filter_tags"] == ["billing", "support"]
    assert [row["doc_id"] for row in first["final"]] == ["doc-a", "doc-b", "doc-c"]
    assert [row["doc_id"] for row in first["semantic"]] == ["doc-a", "doc-b", "doc-c"]
    assert first["final"][0]["matched_tags"] == ["billing"]
    assert first["final"][1]["matched_tags"] == ["billing", "support"]

