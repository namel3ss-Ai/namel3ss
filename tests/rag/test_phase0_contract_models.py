from __future__ import annotations

from namel3ss.rag.contracts import (
    CHUNK_SCHEMA_VERSION,
    CITATION_SCHEMA_VERSION,
    DOCUMENT_SCHEMA_VERSION,
    RETRIEVAL_CONFIG_SCHEMA_VERSION,
    RETRIEVAL_RESULT_SCHEMA_VERSION,
    TRACE_SCHEMA_VERSION,
    build_citation_model,
    build_chunk_model,
    build_document_model,
    build_retrieval_config_model,
    build_retrieval_result_model,
    build_trace_model,
    normalize_document_model,
    normalize_retrieval_config_model,
)
from namel3ss.rag.determinism.json_policy import canonical_contract_json


def test_document_identity_stays_stable_across_versions() -> None:
    first = build_document_model(
        source_type="upload",
        source_identity="team/a/policy.pdf",
        source_uri="file:///policy.pdf",
        content="Policy revision one",
    )
    second = build_document_model(
        source_type="upload",
        source_identity="team/a/policy.pdf",
        source_uri="file:///policy.pdf",
        content="Policy revision two",
    )
    assert first["schema_version"] == DOCUMENT_SCHEMA_VERSION
    assert first["doc_id"] == second["doc_id"]
    assert first["doc_version_id"] != second["doc_version_id"]


def test_normalize_document_model_preserves_unknown_fields_in_extensions() -> None:
    normalized = normalize_document_model(
        {
            "source_type": "connector:gdrive",
            "source_identity": "drive/file/123",
            "owner_team": "security",
            "retention_class": "long",
        }
    )
    assert normalized["schema_version"] == DOCUMENT_SCHEMA_VERSION
    assert normalized["extensions"] == {
        "owner_team": "security",
        "retention_class": "long",
    }


def test_retrieval_config_snapshot_is_canonical_across_input_ordering() -> None:
    first = normalize_retrieval_config_model(
        {
            "top_k": 10,
            "hybrid_weights": {"keyword_weight": 0.4, "semantic_weight": 0.6},
            "filters": {"tags": ["zeta", "alpha"], "team": "docs"},
            "scope": {"documents": ["doc.z", "doc.a"], "collections": ["kb.z", "kb.a"]},
            "parser_version": "pdf@2",
            "chunking_version": "chunk@3",
        }
    )
    second = normalize_retrieval_config_model(
        {
            "scope": {"collections": ["kb.a", "kb.z"], "documents": ["doc.a", "doc.z"]},
            "filters": {"team": "docs", "tags": ["alpha", "zeta"]},
            "hybrid_weights": {"semantic_weight": 0.6, "keyword_weight": 0.4},
            "top_k": 10,
            "chunking_version": "chunk@3",
            "parser_version": "pdf@2",
        }
    )
    assert first["schema_version"] == RETRIEVAL_CONFIG_SCHEMA_VERSION
    assert canonical_contract_json(first, pretty=False) == canonical_contract_json(second, pretty=False)


def test_trace_model_contains_replay_config_and_stable_fingerprint() -> None:
    retrieval_config = build_retrieval_config_model(top_k=6, parser_version="pdf@2", chunking_version="chunk@1")
    first = build_trace_model(
        run_id="run.a",
        input_payload={"message": "policy update"},
        retrieval_config=retrieval_config,
        retrieved_chunk_ids=["chunk.1", "chunk.2"],
        events=[{"event_type": "token", "output": "ok"}],
    )
    second = build_trace_model(
        run_id="run.a",
        input_payload={"message": "policy update"},
        retrieval_config=retrieval_config,
        retrieved_chunk_ids=["chunk.1", "chunk.2"],
        events=[{"event_type": "token", "output": "ok"}],
    )
    changed = build_trace_model(
        run_id="run.a",
        input_payload={"message": "policy update"},
        retrieval_config=retrieval_config,
        retrieved_chunk_ids=["chunk.1", "chunk.3"],
        events=[{"event_type": "token", "output": "ok"}],
    )
    assert first["schema_version"] == TRACE_SCHEMA_VERSION
    assert first["run_determinism_fingerprint"] == second["run_determinism_fingerprint"]
    assert first["run_determinism_fingerprint"] != changed["run_determinism_fingerprint"]


def test_retrieval_config_serialization_is_canonical_snapshot() -> None:
    payload = normalize_retrieval_config_model(
        {
            "top_k": 5,
            "hybrid_weights": {"semantic_weight": 0.75, "keyword_weight": 0.25},
            "rerank_model_id": "rerank.alpha",
            "filters": {"team": "platform", "tags": ["beta", "alpha"]},
            "scope": {"documents": ["doc.b", "doc.a"], "collections": ["kb.2", "kb.1"], "tenant_id": "tenant.a"},
            "parser_version": "pdf@4",
            "chunking_version": "chunk@7",
        }
    )
    assert canonical_contract_json(payload, pretty=False) == (
        '{"chunking_version":"chunk@7","extensions":{},"filters":{"tags":["alpha","beta"],"team":"platform"},'
        '"hybrid_weights":{"keyword_weight":0.25,"semantic_weight":0.75},"parser_version":"pdf@4",'
        '"rerank_model_id":"rerank.alpha","schema_version":"rag.retrieval_config@1",'
        '"scope":{"collections":["kb.1","kb.2"],"documents":["doc.a","doc.b"],"tenant_id":"tenant.a"},"top_k":5}'
    )


def test_chunk_citation_and_retrieval_models_expose_schema_versions() -> None:
    chunk = build_chunk_model(
        doc_id="doc_a",
        page_number=2,
        chunk_index=3,
        text="Policy section A",
    )
    citation = build_citation_model(
        doc_id="doc_a",
        page_number=2,
        chunk_id=chunk["chunk_id"],
        answer_span={"start_char": 5, "end_char": 18},
        preview_target={"page": 2, "anchor": "section a"},
        mention_index=1,
    )
    retrieval_result = build_retrieval_result_model(
        rank=1,
        chunk_id=chunk["chunk_id"],
        doc_id="doc_a",
        page_number=2,
        score=0.83,
        rerank_score=0.91,
        reason_codes=["keyword_overlap", "rerank_top"],
    )
    assert chunk["schema_version"] == CHUNK_SCHEMA_VERSION
    assert citation["schema_version"] == CITATION_SCHEMA_VERSION
    assert retrieval_result["schema_version"] == RETRIEVAL_RESULT_SCHEMA_VERSION
    assert citation["answer_span"] == {"end_char": 18, "start_char": 5}
