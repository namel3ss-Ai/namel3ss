from __future__ import annotations

from namel3ss.rag.contracts import build_chunk_model
from namel3ss.rag.determinism import (
    build_boundary_signature,
    normalize_score,
    sort_citation_rows,
    sort_retrieval_results,
    stable_preview_query,
)


def test_boundary_signature_is_stable_for_whitespace_variants() -> None:
    first = build_boundary_signature(
        doc_id="doc.a",
        page_number=1,
        chunk_index=0,
        text="Policy\nline  one\twith  spaces",
    )
    second = build_boundary_signature(
        doc_id="doc.a",
        page_number=1,
        chunk_index=0,
        text="Policy line one with spaces",
    )
    assert first == second


def test_chunk_id_is_stable_for_whitespace_variants() -> None:
    first = build_chunk_model(
        doc_id="doc.a",
        page_number=3,
        chunk_index=2,
        text="A  sample\n\nparagraph with whitespace",
    )
    second = build_chunk_model(
        doc_id="doc.a",
        page_number=3,
        chunk_index=2,
        text="A sample paragraph with whitespace",
    )
    assert first["boundary_signature"] == second["boundary_signature"]
    assert first["chunk_id"] == second["chunk_id"]


def test_retrieval_sort_policy_uses_contract_tie_break_order() -> None:
    rows = [
        {"doc_id": "doc.b", "page_number": 2, "chunk_id": "chunk.b", "score": 0.9, "rerank_score": 0.7},
        {"doc_id": "doc.a", "page_number": 2, "chunk_id": "chunk.a2", "score": 0.9, "rerank_score": 0.7},
        {"doc_id": "doc.a", "page_number": 1, "chunk_id": "chunk.a1", "score": 0.9, "rerank_score": 0.7},
        {"doc_id": "doc.a", "page_number": 1, "chunk_id": "chunk.a0", "score": 0.9, "rerank_score": 0.8},
        {"doc_id": "doc.c", "page_number": 1, "chunk_id": "chunk.c", "score": 0.8, "rerank_score": 0.95},
    ]
    ordered = sort_retrieval_results(rows)
    assert [entry["chunk_id"] for entry in ordered] == [
        "chunk.a0",
        "chunk.a1",
        "chunk.a2",
        "chunk.b",
        "chunk.c",
    ]


def test_score_normalization_rounding_is_stable() -> None:
    low = normalize_score("0.1234564")
    high = normalize_score("0.1234565")
    assert str(low) == "0.123456"
    assert str(high) == "0.123457"


def test_citation_sort_policy_orders_by_mention_and_source_keys() -> None:
    rows = [
        {"citation_id": "c3", "mention_index": 1, "doc_id": "doc.b", "page_number": 1, "chunk_id": "chunk.2"},
        {"citation_id": "c1", "mention_index": 0, "doc_id": "doc.b", "page_number": 1, "chunk_id": "chunk.1"},
        {"citation_id": "c2", "mention_index": 1, "doc_id": "doc.a", "page_number": 1, "chunk_id": "chunk.1"},
    ]
    ordered = sort_citation_rows(rows)
    assert [entry["citation_id"] for entry in ordered] == ["c1", "c2", "c3"]


def test_stable_preview_query_is_replay_safe() -> None:
    query = stable_preview_query(doc_id="doc.alpha", page_number=12, citation_id="cit.9")
    assert query == "doc=doc.alpha&page=12&cit=cit.9"
