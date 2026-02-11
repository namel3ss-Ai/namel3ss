from __future__ import annotations

from namel3ss.ingestion.policy import ACTION_RETRIEVAL_INCLUDE_WARN, PolicyDecision
from namel3ss.retrieval.api import run_retrieval
from namel3ss.runtime.retrieval.preview_engine import build_preview_rows


def _allow_warn() -> PolicyDecision:
    return PolicyDecision(
        action=ACTION_RETRIEVAL_INCLUDE_WARN,
        allowed=True,
        reason="test",
        required_permissions=(),
        source="test",
    )


def test_preview_rows_are_deterministic_and_tie_break_by_doc_id() -> None:
    rows = [
        {
            "chunk_id": "doc-b:0",
            "document_id": "doc-b",
            "source_name": "Doc B",
            "keyword_overlap": 5,
            "matched_tags": ["beta", "alpha", "alpha"],
        },
        {
            "chunk_id": "doc-a:0",
            "document_id": "doc-a",
            "source_name": "Doc A",
            "keyword_overlap": 5,
            "matched_tags": ["alpha"],
        },
        {
            "chunk_id": "doc-c:0",
            "document_id": "doc-c",
            "source_name": "Doc C",
            "keyword_overlap": 2,
            "matched_tags": ["gamma"],
        },
    ]
    vector_scores = {
        "doc-a:0": 0.7,
        "doc-b:0": 0.7,
        "doc-c:0": 0.9,
    }
    first = build_preview_rows(rows, vector_scores=vector_scores, semantic_weight=0.5)
    second = build_preview_rows(rows, vector_scores=vector_scores, semantic_weight=0.5)
    assert first == second
    assert [entry["doc_id"] for entry in first] == ["doc-a", "doc-b", "doc-c"]
    assert first[0]["matched_tags"] == ["alpha"]
    assert first[1]["matched_tags"] == ["alpha", "beta"]


def test_run_retrieval_preview_is_stable_for_identical_input() -> None:
    state = {
        "ingestion": {
            "doc-a": {"status": "pass"},
            "doc-b": {"status": "pass"},
        },
        "index": {
            "chunks": [
                {
                    "upload_id": "doc-a",
                    "chunk_id": "doc-a:0",
                    "document_id": "doc-a",
                    "source_name": "Doc A",
                    "page_number": 1,
                    "chunk_index": 0,
                    "ingestion_phase": "deep",
                    "keywords": ["alpha", "policy"],
                    "text": "alpha policy details",
                    "tags": ["alpha"],
                },
                {
                    "upload_id": "doc-b",
                    "chunk_id": "doc-b:0",
                    "document_id": "doc-b",
                    "source_name": "Doc B",
                    "page_number": 1,
                    "chunk_index": 1,
                    "ingestion_phase": "deep",
                    "keywords": ["alpha", "guide"],
                    "text": "alpha guide details",
                    "tags": ["beta"],
                },
            ]
        },
    }
    first = run_retrieval(
        query="alpha",
        state=state,
        project_root=None,
        app_path=None,
        policy_decision=_allow_warn(),
    )
    second = run_retrieval(
        query="alpha",
        state=state,
        project_root=None,
        app_path=None,
        policy_decision=_allow_warn(),
    )
    assert first["retrieval_preview"] == second["retrieval_preview"]

