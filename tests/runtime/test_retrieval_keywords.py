from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.ingestion.keywords import extract_keywords
from namel3ss.ingestion.policy import ACTION_RETRIEVAL_INCLUDE_WARN, PolicyDecision
from namel3ss.retrieval.api import run_retrieval


def _state(chunks: list[dict]) -> dict:
    ingestion = {}
    for chunk in chunks:
        upload_id = chunk.get("upload_id")
        if isinstance(upload_id, str):
            ingestion[upload_id] = {"status": "pass"}
    return {"ingestion": ingestion, "index": {"chunks": chunks}}


def _allow_warn() -> PolicyDecision:
    return PolicyDecision(
        action=ACTION_RETRIEVAL_INCLUDE_WARN,
        allowed=True,
        reason="test",
        required_permissions=(),
        source="test",
    )


def test_keyword_extraction_is_deterministic() -> None:
    text = "Alpha and beta: alpha; invoice processing for the account."
    expected = ["alpha", "beta", "invoice", "processing", "account"]
    assert extract_keywords(text) == expected
    assert extract_keywords(text) == expected


def test_keyword_overlap_ranking_prefers_higher_overlap() -> None:
    chunks = [
        {
            "upload_id": "u1",
            "document_id": "u1",
            "source_name": "one.txt",
            "page_number": 2,
            "chunk_index": 0,
            "ingestion_phase": "deep",
            "keywords": ["alpha", "beta"],
            "text": "alpha beta",
        },
        {
            "upload_id": "u2",
            "document_id": "u2",
            "source_name": "two.txt",
            "page_number": 1,
            "chunk_index": 0,
            "ingestion_phase": "deep",
            "keywords": ["alpha"],
            "text": "alpha",
        },
    ]
    result = run_retrieval(
        query="alpha beta",
        state=_state(chunks),
        project_root=None,
        app_path=None,
        policy_decision=_allow_warn(),
    )
    assert result["query"] == "alpha beta"
    assert result["query_keywords"] == ["alpha", "beta"]
    assert result["preferred_quality"] == "pass"
    assert result["included_warn"] is False
    assert result["excluded_blocked"] == 0
    assert result["excluded_warn"] == 0
    assert result["warn_allowed"] is True
    assert result["warn_policy"] == {
        "action": ACTION_RETRIEVAL_INCLUDE_WARN,
        "decision": "allowed",
        "reason": "test",
    }
    assert result["tier"] == {
        "requested": "auto",
        "selected": "deep",
        "reason": "deep_available",
        "available": ["deep"],
        "counts": {"deep": 2, "quick": 0},
    }
    assert result["results"] == [
        {
            "upload_id": "u1",
            "chunk_id": "u1:0",
            "quality": "pass",
            "low_quality": False,
            "text": "alpha beta",
            "document_id": "u1",
            "source_name": "one.txt",
            "page_number": 2,
            "chunk_index": 0,
            "ingestion_phase": "deep",
            "keywords": ["alpha", "beta"],
            "keyword_source": "stored",
            "keyword_matches": ["alpha", "beta"],
            "keyword_overlap": 2,
        },
        {
            "upload_id": "u2",
            "chunk_id": "u2:0",
            "quality": "pass",
            "low_quality": False,
            "text": "alpha",
            "document_id": "u2",
            "source_name": "two.txt",
            "page_number": 1,
            "chunk_index": 0,
            "ingestion_phase": "deep",
            "keywords": ["alpha"],
            "keyword_source": "stored",
            "keyword_matches": ["alpha"],
            "keyword_overlap": 1,
        },
    ]
    assert isinstance(result.get("retrieval_plan"), dict)
    assert isinstance(result.get("retrieval_trace"), list)
    assert isinstance(result.get("trust_score_details"), dict)


def test_keyword_overlap_tiebreaks_by_page_and_chunk() -> None:
    chunks = [
        {
            "upload_id": "u1",
            "document_id": "u1",
            "source_name": "one.txt",
            "page_number": 2,
            "chunk_index": 1,
            "ingestion_phase": "deep",
            "keywords": ["alpha"],
            "text": "alpha second",
        },
        {
            "upload_id": "u1",
            "document_id": "u1",
            "source_name": "one.txt",
            "page_number": 1,
            "chunk_index": 0,
            "ingestion_phase": "deep",
            "keywords": ["alpha"],
            "text": "alpha first",
        },
    ]
    result = run_retrieval(
        query="alpha",
        state=_state(chunks),
        project_root=None,
        app_path=None,
        policy_decision=_allow_warn(),
    )
    assert result["results"] == [
        {
            "upload_id": "u1",
            "chunk_id": "u1:0",
            "quality": "pass",
            "low_quality": False,
            "text": "alpha first",
            "document_id": "u1",
            "source_name": "one.txt",
            "page_number": 1,
            "chunk_index": 0,
            "ingestion_phase": "deep",
            "keywords": ["alpha"],
            "keyword_source": "stored",
            "keyword_matches": ["alpha"],
            "keyword_overlap": 1,
        },
        {
            "upload_id": "u1",
            "chunk_id": "u1:1",
            "quality": "pass",
            "low_quality": False,
            "text": "alpha second",
            "document_id": "u1",
            "source_name": "one.txt",
            "page_number": 2,
            "chunk_index": 1,
            "ingestion_phase": "deep",
            "keywords": ["alpha"],
            "keyword_source": "stored",
            "keyword_matches": ["alpha"],
            "keyword_overlap": 1,
        },
    ]


def test_missing_keywords_fail_explicitly() -> None:
    chunks = [
        {
            "upload_id": "u1",
            "document_id": "u1",
            "source_name": "one.txt",
            "page_number": 1,
            "chunk_index": 0,
            "ingestion_phase": "deep",
            "text": "",
        }
    ]
    with pytest.raises(Namel3ssError):
        run_retrieval(
            query="alpha",
            state=_state(chunks),
            project_root=None,
            app_path=None,
            policy_decision=_allow_warn(),
        )
