from __future__ import annotations

from namel3ss.ingestion.policy import ACTION_RETRIEVAL_INCLUDE_WARN, PolicyDecision
from namel3ss.retrieval.api import run_retrieval


def _allow_warn() -> PolicyDecision:
    return PolicyDecision(
        action=ACTION_RETRIEVAL_INCLUDE_WARN,
        allowed=True,
        reason="test",
        required_permissions=(),
        source="test",
    )


def _state() -> dict:
    return {
        "active_docs": ["doc-b"],
        "ingestion": {
            "doc-a": {"status": "pass"},
            "doc-b": {"status": "pass"},
            "doc-c": {"status": "pass"},
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
                    "keywords": ["alpha", "invoice"],
                    "text": "alpha invoice details",
                    "tags": ["finance", "billing", "finance"],
                },
                {
                    "upload_id": "doc-b",
                    "chunk_id": "doc-b:0",
                    "document_id": "doc-b",
                    "source_name": "Doc B",
                    "page_number": 2,
                    "chunk_index": 0,
                    "ingestion_phase": "deep",
                    "keywords": ["alpha", "support"],
                    "text": "alpha support details",
                    "tags": ["support"],
                },
                {
                    "upload_id": "doc-c",
                    "chunk_id": "doc-c:0",
                    "document_id": "doc-c",
                    "source_name": "Doc C",
                    "page_number": 3,
                    "chunk_index": 0,
                    "ingestion_phase": "deep",
                    "keywords": ["alpha", "ops"],
                    "text": "alpha operations details",
                    "tags": ["ops"],
                },
            ]
        },
    }


def test_filter_tags_parameter_limits_retrieval_scope() -> None:
    result = run_retrieval(
        query="alpha",
        state=_state(),
        project_root=None,
        app_path=None,
        filter_tags=["billing", "finance"],
        policy_decision=_allow_warn(),
    )
    assert result["filter_tags"] == ["billing", "finance"]
    assert [entry["document_id"] for entry in result["results"]] == ["doc-a"]
    assert result["results"][0]["matched_tags"] == ["billing", "finance"]


def test_filter_tags_falls_back_to_active_docs_state() -> None:
    state = _state()
    for chunk in state["index"]["chunks"]:
        chunk.pop("tags", None)
    result = run_retrieval(
        query="alpha",
        state=state,
        project_root=None,
        app_path=None,
        filter_tags=None,
        policy_decision=_allow_warn(),
    )
    assert result["filter_tags"] == ["doc-b"]
    assert [entry["document_id"] for entry in result["results"]] == ["doc-b"]


def test_filter_tags_empty_result_is_deterministic() -> None:
    result = run_retrieval(
        query="alpha",
        state=_state(),
        project_root=None,
        app_path=None,
        filter_tags=["missing-tag"],
        policy_decision=_allow_warn(),
    )
    assert result["filter_tags"] == ["missing-tag"]
    assert result["results"] == []
    assert result["retrieval_preview"] == []
