from __future__ import annotations

import pytest

from namel3ss.runtime.citations.citation_normalizer import CitationInvariantError, normalize_citations


def test_citation_normalizer_is_deterministic_and_snippet_first() -> None:
    citations = [
        {
            "document_id": "doc-b",
            "page_number": 3,
            "chunk_index": 1,
            "snippet": "Second snippet",
            "title": "B",
            "score": 0.4,
        },
        {
            "document_id": "doc-a",
            "page_number": 1,
            "chunk_index": 0,
            "snippet": "First snippet",
            "title": "A",
            "score": 0.9,
        },
    ]
    first = normalize_citations(citations)
    second = normalize_citations(citations)
    assert first == second
    assert [entry["source_id"] for entry in first["citations"]] == ["doc-a:1:0", "doc-b:3:1"]
    assert list(first["citations"][0].keys())[0] == "snippet"


def test_citation_normalizer_requires_snippet() -> None:
    with pytest.raises(CitationInvariantError) as excinfo:
        normalize_citations(
            [
                {
                    "document_id": "doc-a",
                    "page_number": 1,
                    "chunk_index": 0,
                    "snippet": "",
                }
            ]
        )
    assert excinfo.value.error_code == "N3E_CITATION_INVARIANT_BROKEN"
