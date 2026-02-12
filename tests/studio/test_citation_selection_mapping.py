from __future__ import annotations

import pytest

from namel3ss.studio.citations.selection_mapping import map_citation_selection


def test_citation_selection_mapping_builds_preview_url() -> None:
    mapped = map_citation_selection(
        {
            "document_id": "doc-7",
            "page_number": 4,
            "chunk_id": "doc-7:3",
            "source_id": "doc-7:4:3",
        }
    )
    assert mapped == {
        "chunk_id": "doc-7:3",
        "document_id": "doc-7",
        "page_number": 4,
        "preview_url": "/api/documents/doc-7/pages/4?chunk_id=doc-7:3",
        "source_id": "doc-7:4:3",
    }


def test_citation_selection_mapping_can_derive_doc_and_page_from_source_id() -> None:
    mapped = map_citation_selection({"source_id": "doc-9:2:5"})
    assert mapped["document_id"] == "doc-9"
    assert mapped["page_number"] == 2
    assert mapped["preview_url"] == "/api/documents/doc-9/pages/2?source_id=doc-9:2:5"


def test_citation_selection_mapping_requires_doc_and_page() -> None:
    with pytest.raises(ValueError) as excinfo:
        map_citation_selection({})
    assert "N3E_CITATION_INVARIANT_BROKEN" in str(excinfo.value)
