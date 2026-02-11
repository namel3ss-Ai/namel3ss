from __future__ import annotations

from namel3ss.determinism import canonical_json_dumps
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
        "retrieval": {"tuning": {"semantic_weight": 0.5, "semantic_k": 10, "lexical_k": 10, "final_top_k": 10}},
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
                    "keywords": ["alpha", "billing"],
                    "text": "alpha billing context",
                    "tags": ["billing"],
                },
                {
                    "upload_id": "doc-b",
                    "chunk_id": "doc-b:0",
                    "document_id": "doc-b",
                    "source_name": "Doc B",
                    "page_number": 1,
                    "chunk_index": 1,
                    "ingestion_phase": "deep",
                    "keywords": ["alpha", "support"],
                    "text": "alpha support context",
                    "tags": ["support"],
                },
            ]
        },
    }


def test_repeat_retrieval_trace_payload_is_byte_identical() -> None:
    first = run_retrieval(
        query="alpha",
        state=_state(),
        project_root=None,
        app_path=None,
        policy_decision=_allow_warn(),
        diagnostics_trace_enabled=True,
    )
    second = run_retrieval(
        query="alpha",
        state=_state(),
        project_root=None,
        app_path=None,
        policy_decision=_allow_warn(),
        diagnostics_trace_enabled=True,
    )

    first_trace = first.get("retrieval_trace_diagnostics") or {}
    second_trace = second.get("retrieval_trace_diagnostics") or {}
    assert canonical_json_dumps(first_trace, pretty=False, drop_run_keys=False) == canonical_json_dumps(
        second_trace,
        pretty=False,
        drop_run_keys=False,
    )
