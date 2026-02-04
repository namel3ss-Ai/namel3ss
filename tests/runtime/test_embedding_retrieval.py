from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ingestion.embeddings import store_chunk_embeddings
from namel3ss.ingestion.hash import hash_chunk
from namel3ss.ingestion.keywords import extract_keywords, keyword_matches
from namel3ss.ingestion.policy import ACTION_RETRIEVAL_INCLUDE_WARN, PolicyDecision
from namel3ss.retrieval.api import run_retrieval
from namel3ss.runtime.embeddings.service import embed_text, resolve_embedding_model
from namel3ss.runtime.embeddings.store import get_embedding_store


def _embedding_config(*, candidate_limit: int = 1) -> AppConfig:
    config = AppConfig()
    config.embedding.provider = "test"
    config.embedding.model = "test"
    config.embedding.version = "v1"
    config.embedding.dims = 2
    config.embedding.precision = 3
    config.embedding.candidate_limit = candidate_limit
    config.persistence.target = "memory"
    return config


def _policy_allow() -> PolicyDecision:
    return PolicyDecision(
        action=ACTION_RETRIEVAL_INCLUDE_WARN,
        allowed=True,
        reason=None,
        required_permissions=(),
        source="test",
    )


def _chunk(
    upload_id: str,
    text: str,
    *,
    page_number: int = 1,
    chunk_index: int = 0,
    phase: str = "deep",
) -> dict:
    chunk_hash = hash_chunk(
        document_id=upload_id,
        page_number=page_number,
        chunk_index=chunk_index,
        text=text,
    )
    return {
        "upload_id": upload_id,
        "chunk_id": f"{upload_id}:{chunk_index}",
        "document_id": upload_id,
        "source_name": f"{upload_id}.txt",
        "page_number": page_number,
        "chunk_index": chunk_index,
        "ingestion_phase": phase,
        "text": text,
        "chunk_hash": chunk_hash,
        "keywords": extract_keywords(text),
    }


def _state(chunks: list[dict]) -> dict:
    ingestion = {entry.get("upload_id"): {"status": "pass"} for entry in chunks if isinstance(entry, dict)}
    return {"ingestion": ingestion, "index": {"chunks": chunks}}


def _expected_result(chunk: dict, query_keywords: list[str]) -> dict:
    matches = keyword_matches(query_keywords, chunk.get("keywords") or [])
    return {
        "upload_id": chunk["upload_id"],
        "chunk_id": chunk["chunk_id"],
        "quality": "pass",
        "low_quality": False,
        "text": chunk["text"],
        "document_id": chunk["document_id"],
        "source_name": chunk["source_name"],
        "page_number": chunk["page_number"],
        "chunk_index": chunk["chunk_index"],
        "ingestion_phase": chunk["ingestion_phase"],
        "keywords": chunk["keywords"],
        "keyword_source": "stored",
        "keyword_matches": matches,
        "keyword_overlap": len(matches),
    }


def test_embeddings_cached_by_chunk_hash(tmp_path: Path) -> None:
    config = _embedding_config(candidate_limit=2)
    app_path = tmp_path / "app.ai"
    chunk = _chunk("doc-1", "alpha content")
    first = store_chunk_embeddings(
        [chunk],
        upload_id="doc-1",
        config=config,
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
        capabilities=("embedding",),
    )
    model = resolve_embedding_model(config)
    assert first == {"enabled": True, "stored": 1, "cached": 0, "model_id": model.model_id}
    second = store_chunk_embeddings(
        [chunk],
        upload_id="doc-1",
        config=config,
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
        capabilities=("embedding",),
    )
    assert second == {"enabled": True, "stored": 0, "cached": 1, "model_id": model.model_id}
    store = get_embedding_store(config, project_root=str(tmp_path), app_path=app_path.as_posix())
    records = store.get_records(model_id=model.model_id, chunk_hashes=[chunk["chunk_hash"]])
    assert records[chunk["chunk_hash"]].vector == embed_text(chunk["text"], model)


def test_embeddings_only_for_deep_chunks(tmp_path: Path) -> None:
    config = _embedding_config(candidate_limit=2)
    app_path = tmp_path / "app.ai"
    deep_chunk = _chunk("doc-1", "alpha content", page_number=1, chunk_index=0, phase="deep")
    quick_chunk = _chunk("doc-1", "beta content", page_number=2, chunk_index=1, phase="quick")
    store_chunk_embeddings(
        [deep_chunk, quick_chunk],
        upload_id="doc-1",
        config=config,
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
        capabilities=("embedding",),
    )
    model = resolve_embedding_model(config)
    store = get_embedding_store(config, project_root=str(tmp_path), app_path=app_path.as_posix())
    records = store.get_records(
        model_id=model.model_id,
        chunk_hashes=[deep_chunk["chunk_hash"], quick_chunk["chunk_hash"]],
    )
    assert deep_chunk["chunk_hash"] in records
    assert quick_chunk["chunk_hash"] not in records


def test_embedding_disabled_does_not_change_retrieval(tmp_path: Path) -> None:
    config = _embedding_config(candidate_limit=2)
    app_path = tmp_path / "app.ai"
    chunks = [
        _chunk("doc-1", "alpha content", page_number=1, chunk_index=0, phase="deep"),
        _chunk("doc-2", "alpha follow-up", page_number=2, chunk_index=0, phase="quick"),
    ]
    state = _state(chunks)
    first = run_retrieval(
        query="alpha",
        state=state,
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
        explain=True,
        policy_decision=_policy_allow(),
        config=config,
        capabilities=("uploads",),
    )
    second = run_retrieval(
        query="alpha",
        state=state,
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
        explain=True,
        policy_decision=_policy_allow(),
        config=config,
        capabilities=(),
    )
    query_keywords = extract_keywords("alpha")
    assert first["results"] == [
        _expected_result(chunks[0], query_keywords),
        _expected_result(chunks[1], query_keywords),
    ]
    assert first == second
    assert first["explain"]["embedding"] == {
        "enabled": False,
        "model_id": None,
        "candidate_count": 0,
        "candidates": [],
    }


def test_embedding_retrieval_includes_semantic_candidate(tmp_path: Path) -> None:
    config = _embedding_config(candidate_limit=1)
    app_path = tmp_path / "app.ai"
    chunks = [
        _chunk("doc-1", "omega signal", page_number=1, chunk_index=0, phase="deep"),
        _chunk("doc-2", "beta content", page_number=2, chunk_index=0, phase="deep"),
    ]
    store_chunk_embeddings(
        [chunks[0]],
        upload_id="doc-1",
        config=config,
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
        capabilities=("embedding",),
    )
    store_chunk_embeddings(
        [chunks[1]],
        upload_id="doc-2",
        config=config,
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
        capabilities=("embedding",),
    )
    state = _state(chunks)
    first = run_retrieval(
        query="alpha",
        state=state,
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
        explain=True,
        policy_decision=_policy_allow(),
        config=config,
        capabilities=("embedding",),
    )
    second = run_retrieval(
        query="alpha",
        state=state,
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
        explain=True,
        policy_decision=_policy_allow(),
        config=config,
        capabilities=("embedding",),
    )
    query_keywords = extract_keywords("alpha")
    assert first["results"] == [_expected_result(chunks[0], query_keywords)]
    assert first == second
    explain = first["explain"]
    assert explain["ordering"] == "ingestion_phase, keyword_overlap, page_number, chunk_index, chunk_id"
    assert explain["embedding"] == {
        "enabled": True,
        "model_id": "test:test:v1",
        "candidate_count": 1,
        "candidates": [{"chunk_id": "doc-1:0", "score": 1.0}],
    }
    assert explain["candidates"] == [
        {
            "chunk_id": "doc-1:0",
            "ingestion_phase": "deep",
            "keyword_overlap": 0,
            "page_number": 1,
            "chunk_index": 0,
            "vector_score": 1.0,
            "decision": "selected",
            "reason": "top_k",
        },
        {
            "chunk_id": "doc-2:0",
            "ingestion_phase": "deep",
            "keyword_overlap": 0,
            "page_number": 2,
            "chunk_index": 0,
            "vector_score": 0.0,
            "decision": "excluded",
            "reason": "filtered",
        },
    ]


def test_embedding_unavailable_records_are_deterministic(tmp_path: Path) -> None:
    config = _embedding_config(candidate_limit=2)
    app_path = tmp_path / "app.ai"
    ok_chunk = _chunk("doc-1", "alpha content", page_number=1, chunk_index=0, phase="deep")
    fail_chunk = _chunk("doc-1", "fail omega", page_number=2, chunk_index=1, phase="deep")
    store_chunk_embeddings(
        [ok_chunk, fail_chunk],
        upload_id="doc-1",
        config=config,
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
        capabilities=("embedding",),
    )
    model = resolve_embedding_model(config)
    store = get_embedding_store(config, project_root=str(tmp_path), app_path=app_path.as_posix())
    records = store.get_records(model_id=model.model_id, chunk_hashes=[ok_chunk["chunk_hash"], fail_chunk["chunk_hash"]])
    assert records[ok_chunk["chunk_hash"]].status == "ok"
    assert records[fail_chunk["chunk_hash"]].status == "unavailable"
    state = _state([ok_chunk, fail_chunk])
    result = run_retrieval(
        query="alpha",
        state=state,
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
        explain=True,
        policy_decision=_policy_allow(),
        config=config,
        capabilities=("embedding",),
    )
    query_keywords = extract_keywords("alpha")
    assert result["results"] == [_expected_result(ok_chunk, query_keywords)]
    assert result["explain"]["embedding"]["candidate_count"] == 1
    assert result["explain"]["embedding"]["candidates"] == [{"chunk_id": ok_chunk["chunk_id"], "score": 1.0}]


def test_embedding_missing_model_fails(tmp_path: Path) -> None:
    config = _embedding_config()
    config.embedding.model = ""
    app_path = tmp_path / "app.ai"
    expected = build_guidance_message(
        what="Embedding model is missing.",
        why="Embeddings require a pinned model identity.",
        fix="Set embedding.model to a non-empty string.",
        example='[embedding]\nmodel = "hash"\nversion = "v1"',
    )
    with pytest.raises(Namel3ssError) as excinfo:
        run_retrieval(
            query="alpha",
            state={"ingestion": {}, "index": {"chunks": []}},
            project_root=str(tmp_path),
            app_path=app_path.as_posix(),
            config=config,
            capabilities=("embedding",),
        )
    assert str(excinfo.value) == expected


def test_embedding_store_missing_url_fails(tmp_path: Path) -> None:
    config = _embedding_config()
    config.persistence.target = "postgres"
    config.persistence.database_url = None
    app_path = tmp_path / "app.ai"
    expected = build_guidance_message(
        what="Postgres embedding store is missing N3_DATABASE_URL.",
        why="Embedding persistence needs a database URL.",
        fix="Set N3_DATABASE_URL or configure persistence.database_url.",
        example="N3_PERSIST_TARGET=postgres N3_DATABASE_URL=postgres://user:pass@host/db",
    )
    with pytest.raises(Namel3ssError) as excinfo:
        run_retrieval(
            query="alpha",
            state={"ingestion": {}, "index": {"chunks": []}},
            project_root=str(tmp_path),
            app_path=app_path.as_posix(),
            config=config,
            capabilities=("embedding",),
        )
    assert str(excinfo.value) == expected
