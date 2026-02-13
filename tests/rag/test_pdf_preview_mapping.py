from __future__ import annotations

from urllib.parse import quote

from namel3ss.rag.determinism import stable_preview_query
from namel3ss.rag.retrieval.citation_mapper import map_answer_citations
from namel3ss.rag.retrieval.highlight_resolver import (
    HIGHLIGHT_MODE_ANCHOR,
    HIGHLIGHT_MODE_BBOX,
    HIGHLIGHT_MODE_TOKEN_POSITIONS,
    resolve_highlight_target,
)
from namel3ss.rag.retrieval.pdf_preview_mapper import build_pdf_preview_routes, citation_color_index


def test_citation_mapper_is_deterministic_for_multi_chunk_answer() -> None:
    answer_text = "Answer cites [doc-b:1] before [doc-a:0]."
    citation_chunk_ids = ["doc-b:1", "doc-a:0"]
    retrieval_trace = [
        {"chunk_id": "doc-a:0", "document_id": "doc-a", "page_number": 2},
        {"chunk_id": "doc-b:1", "document_id": "doc-b", "page_number": 1},
    ]
    index_chunks = [
        {
            "chunk_id": "doc-a:0",
            "doc_id": "doc-a",
            "page_number": 2,
            "span": {"start_char": 10, "end_char": 28},
            "text": "Alpha policy text",
        },
        {
            "chunk_id": "doc-b:1",
            "doc_id": "doc-b",
            "page_number": 1,
            "token_positions": [
                {"index": 0, "token": "Beta", "start_char": 3, "end_char": 7},
                {"index": 1, "token": "policy", "start_char": 8, "end_char": 14},
            ],
            "text": "Beta policy text",
        },
    ]

    first = map_answer_citations(
        answer_text=answer_text,
        citation_chunk_ids=citation_chunk_ids,
        retrieval_trace=retrieval_trace,
        index_chunks=index_chunks,
    )
    second = map_answer_citations(
        answer_text=answer_text,
        citation_chunk_ids=citation_chunk_ids,
        retrieval_trace=retrieval_trace,
        index_chunks=index_chunks,
    )

    assert first == second
    assert [entry["chunk_id"] for entry in first] == ["doc-b:1", "doc-a:0"]
    assert first[0]["preview_target"]["page"] == 1
    assert first[0]["preview_target"]["token_positions"][0]["token"] == "Beta"
    assert first[1]["preview_target"]["span"] == {"end_char": 28, "start_char": 10}
    assert first[0]["extensions"]["deep_link_query"] == stable_preview_query(
        doc_id="doc-b",
        page_number=1,
        citation_id=first[0]["citation_id"],
    )


def test_pdf_preview_routes_are_deterministic_and_carry_color_index() -> None:
    citations = [
        {
            "citation_id": "cit.alpha",
            "chunk_id": "doc-a:0",
            "doc_id": "doc-a",
            "page_number": 3,
            "preview_target": {"page": 3, "span": {"start_char": 5, "end_char": 20}},
            "extensions": {"snippet": "Alpha section"},
        },
        {
            "citation_id": "cit.beta",
            "chunk_id": "doc-b:1",
            "doc_id": "doc-b",
            "page_number": 1,
            "preview_target": {"page": 1, "bbox": [0.1, 0.2, 0.3, 0.4]},
            "extensions": {"snippet": "Beta section"},
        },
    ]

    first = build_pdf_preview_routes(citations=citations, snippet_by_chunk={})
    second = build_pdf_preview_routes(citations=citations, snippet_by_chunk={})

    assert first == second
    assert [entry["citation_id"] for entry in first] == ["cit.beta", "cit.alpha"]
    assert first[0]["preview_url"] == (
        f"/api/documents/{quote('doc-b', safe='')}/pages/1?chunk_id={quote('doc-b:1', safe='')}&citation_id={quote('cit.beta', safe='')}"
    )
    assert first[0]["highlight_mode"] == HIGHLIGHT_MODE_BBOX
    assert 0 <= first[0]["color_index"] <= 7
    assert first[0]["color_index"] == citation_color_index("cit.beta")


def test_highlight_resolver_uses_fixed_fallback_order() -> None:
    page_text = "Alpha words for token span and anchor matching."

    bbox_first = resolve_highlight_target(
        page_text=page_text,
        bbox=[0.2, 0.3, 0.4, 0.5],
        span={"start_char": 0, "end_char": 5},
        token_positions=[{"index": 0, "token": "Alpha", "start_char": 0, "end_char": 5}],
        anchor="Alpha",
    )
    assert bbox_first["resolver"] == HIGHLIGHT_MODE_BBOX
    assert bbox_first["status"] == "exact"

    token_fallback = resolve_highlight_target(
        page_text=page_text,
        token_positions=[
            {"index": 0, "token": "token", "start_char": 16, "end_char": 21},
            {"index": 1, "token": "span", "start_char": 22, "end_char": 26},
        ],
    )
    assert token_fallback["resolver"] == HIGHLIGHT_MODE_TOKEN_POSITIONS
    assert token_fallback["start_char"] == 16
    assert token_fallback["end_char"] == 26

    anchor_fallback = resolve_highlight_target(page_text=page_text, anchor="anchor matching")
    assert anchor_fallback["resolver"] == HIGHLIGHT_MODE_ANCHOR
    assert anchor_fallback["status"] == "exact"
