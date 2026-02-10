from __future__ import annotations

import pytest

from namel3ss.runtime.components.citation_panel import (
    CitationPanelError,
    build_citation_panel_payload,
    merge_citations,
    normalize_citation_state,
    select_citation,
)
from namel3ss.runtime.components.document_library import (
    DocumentLibraryError,
    normalize_document_library_state,
    remove_document,
    select_document,
    upsert_document,
)
from namel3ss.runtime.components.explain_mode import (
    ExplainModeError,
    build_explain_mode_payload,
)
from namel3ss.runtime.components.ingestion_progress import (
    apply_ingestion_events,
    normalize_ingestion_progress_state,
)



def test_citation_panel_merge_and_select_are_deterministic() -> None:
    state = normalize_citation_state({"citations": [{"id": "c2", "title": "Two"}, {"id": "c1", "title": "One"}]})
    merged = merge_citations(state, [{"id": "c1", "snippet": "snippet"}, {"id": "c3", "title": "Three"}])
    assert [entry["id"] for entry in merged["citations"]] == ["c2", "c1", "c3"]
    selected = select_citation(merged, "c1")
    payload = build_citation_panel_payload(selected, component_id="citation.panel")
    assert payload["selected_id"] == "c1"



def test_citation_panel_unknown_selection_raises() -> None:
    with pytest.raises(CitationPanelError):
        select_citation({"citations": [{"id": "c1"}]}, "missing")



def test_document_library_upsert_select_and_remove() -> None:
    state = normalize_document_library_state(None)
    state = upsert_document(state, document_id="doc-2", name="B")
    state = upsert_document(state, document_id="doc-1", name="A")
    assert [entry["id"] for entry in state["documents"]] == ["doc-1", "doc-2"]
    state = select_document(state, "doc-2")
    assert state["selected_document_id"] == "doc-2"
    state = remove_document(state, "doc-2")
    assert state["selected_document_id"] is None



def test_document_library_unknown_document_raises() -> None:
    with pytest.raises(DocumentLibraryError):
        remove_document({"documents": [{"id": "doc-1", "name": "One"}]}, "doc-2")



def test_ingestion_progress_events_are_ordered() -> None:
    state = apply_ingestion_events(
        normalize_ingestion_progress_state(None),
        [
            {"id": "late", "type": "ingestion.percent.set", "percent": 90, "order": 2},
            {"id": "early", "type": "ingestion.stage.set", "stage": "uploading", "order": 1},
        ],
    )
    assert state["status"] == "uploading"
    assert state["percent"] == 90



def test_explain_mode_is_studio_only_by_default() -> None:
    with pytest.raises(ExplainModeError):
        build_explain_mode_payload(
            {"entries": [{"chunk_id": "c1", "score": 1.0}]},
            component_id="explain.1",
            studio_mode=False,
            allow_runtime=False,
        )
    payload = build_explain_mode_payload(
        {"entries": [{"chunk_id": "c1", "score": 1.0}]},
        component_id="explain.1",
        studio_mode=True,
    )
    assert payload["type"] == "component.explain_mode"
    assert payload["entries"][0]["chunk_id"] == "c1"
