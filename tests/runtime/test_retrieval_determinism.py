from __future__ import annotations

from namel3ss.retrieval.api import run_retrieval


def _state() -> dict:
    return {
        "active_docs": ["doc-a", "doc-b"],
        "ingestion": {
            "doc-a": {"status": "pass", "fallback_used": "ocr"},
            "doc-b": {"status": "pass"},
        },
        "index": {
            "chunks": [
                {
                    "upload_id": "doc-a",
                    "chunk_id": "doc-a:0",
                    "document_id": "doc-a",
                    "source_name": "a.txt",
                    "page_number": 1,
                    "chunk_index": 0,
                    "ingestion_phase": "deep",
                    "text": "alpha policy contract",
                    "keywords": ["alpha", "policy", "contract"],
                },
                {
                    "upload_id": "doc-b",
                    "chunk_id": "doc-b:0",
                    "document_id": "doc-b",
                    "source_name": "b.txt",
                    "page_number": 2,
                    "chunk_index": 0,
                    "ingestion_phase": "quick",
                    "text": "alpha checklist process",
                    "keywords": ["alpha", "checklist", "process"],
                },
            ]
        },
    }


def test_retrieval_plan_trace_and_trust_are_replayable() -> None:
    state = _state()
    first = run_retrieval(query="alpha", state=state, project_root=None, app_path=None, limit=2)
    second = run_retrieval(query="alpha", state=state, project_root=None, app_path=None, limit=2)
    assert first == second

    plan = first.get("retrieval_plan")
    trace = first.get("retrieval_trace")
    trust = first.get("trust_score_details")
    assert isinstance(plan, dict)
    assert isinstance(trace, list)
    assert isinstance(trust, dict)

    assert [entry["chunk_id"] for entry in trace] == ["doc-a:0", "doc-b:0"]
    assert [entry["rank"] for entry in trace] == [1, 2]
    assert plan["scope"]["active"] == ["doc-a", "doc-b"]
    assert plan["ordering"] == "ingestion_phase, keyword_overlap, page_number, chunk_index"
    assert 0.0 <= float(trust["score"]) <= 1.0
