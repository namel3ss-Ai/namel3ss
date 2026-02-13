from __future__ import annotations

from namel3ss.rag.determinism.id_policy import build_doc_id
from namel3ss.rag.ingestion import run_connector_sync, run_ingestion_pipeline
from namel3ss.rag.retrieval import run_retrieval_service, upsert_collection_membership
from namel3ss.rag.retrieval.scope_service import apply_retrieval_scope


def test_connector_sync_checkpoint_and_jobs_are_deterministic() -> None:
    state: dict = {}
    records = [
        {
            "collection_ids": ["kb.ops", "kb.all"],
            "content": "Alpha runbook line.",
            "cursor": "0002",
            "source_identity": "drive/alpha.txt",
            "source_uri": "gdrive://drive/alpha.txt",
            "title": "alpha.txt",
        },
        {
            "collection_ids": ["kb.all"],
            "content": "Beta runbook line.",
            "cursor": "0001",
            "source_identity": "drive/beta.txt",
            "source_uri": "gdrive://drive/beta.txt",
            "title": "beta.txt",
        },
        {
            "collection_ids": ["kb.all"],
            "content": "Alpha runbook line older duplicate.",
            "cursor": "0001",
            "source_identity": "drive/alpha.txt",
            "source_uri": "gdrive://drive/alpha.txt",
            "title": "alpha.txt",
        },
    ]

    first = run_connector_sync(
        state=state,
        connector_id="connector.gdrive",
        records=records,
    )
    second = run_connector_sync(
        state=state,
        connector_id="connector.gdrive",
        records=records,
    )
    third = run_connector_sync(
        state=state,
        connector_id="connector.gdrive",
        records=records,
    )

    assert first["checkpoint"]["cursor"] == "0002"
    assert second["checkpoint"]["cursor"] == "0002"
    assert second["job"]["upserted"] == 0
    assert second["job"]["deleted"] == 0
    assert second["job"]["skipped"] == 2
    assert third["job"]["job_id"] == second["job"]["job_id"]

    jobs = state.get("rag_sync", {}).get("jobs", [])
    assert isinstance(jobs, list)
    assert len(jobs) == 2
    assert [job["cursor"] for job in jobs] == ["0002", "0002"]
    assert [job["upserted"] for job in jobs] == [0, 2]

    alpha_doc_id = build_doc_id(source_type="connector:gdrive", source_identity="drive/alpha.txt")
    beta_doc_id = build_doc_id(source_type="connector:gdrive", source_identity="drive/beta.txt")
    all_docs = sorted([alpha_doc_id, beta_doc_id])

    scope_state = state.get("rag_scope", {})
    collections = scope_state.get("collections", [])
    assert collections == [
        {
            "collection_id": "kb.all",
            "connector_id": "",
            "documents": all_docs,
            "name": "kb.all",
            "source_type": "",
        },
        {
            "collection_id": "kb.ops",
            "connector_id": "",
            "documents": [alpha_doc_id],
            "name": "kb.ops",
            "source_type": "",
        },
    ]


def test_connector_sync_delete_removes_doc_and_membership() -> None:
    state: dict = {}
    inserted = run_connector_sync(
        state=state,
        connector_id="connector.gdrive",
        records=[
            {
                "collection_ids": ["kb.ops"],
                "content": "Delete path content.",
                "cursor": "0001",
                "source_identity": "drive/delete-me.txt",
                "source_uri": "gdrive://drive/delete-me.txt",
                "title": "delete-me.txt",
            }
        ],
    )
    doc_id = next(iter(inserted["checkpoint"]["doc_versions"].keys()))
    expected_doc_id = build_doc_id(source_type="connector:gdrive", source_identity=doc_id)

    deleted = run_connector_sync(
        state=state,
        connector_id="connector.gdrive",
        records=[
            {
                "cursor": "0002",
                "deleted": True,
                "source_identity": "drive/delete-me.txt",
            }
        ],
    )

    assert deleted["job"]["deleted"] == 1
    assert expected_doc_id not in state.get("ingestion", {})
    chunks = state.get("index", {}).get("chunks", [])
    assert all(chunk.get("upload_id") != expected_doc_id for chunk in chunks)
    assert state.get("rag_scope", {}).get("collections", []) == []


def test_apply_retrieval_scope_filters_index_and_ingestion() -> None:
    state = {
        "index": {
            "chunks": [
                {"document_id": "doc.a", "upload_id": "doc.a", "chunk_id": "doc.a:0", "text": "alpha"},
                {"document_id": "doc.b", "upload_id": "doc.b", "chunk_id": "doc.b:0", "text": "beta"},
                {"document_id": "doc.c", "upload_id": "doc.c", "chunk_id": "doc.c:0", "text": "gamma"},
            ]
        },
        "ingestion": {
            "doc.a": {"status": "pass"},
            "doc.b": {"status": "pass"},
            "doc.c": {"status": "pass"},
        },
    }
    upsert_collection_membership(state, collection_id="kb.one", document_id="doc.b", name="kb.one")
    upsert_collection_membership(state, collection_id="kb.one", document_id="doc.a", name="kb.one")

    scoped_state, summary = apply_retrieval_scope(
        state=state,
        scope={"collections": ["kb.one"], "documents": ["doc.c"]},
    )

    assert summary == {
        "active": True,
        "requested": {
            "collections": ["kb.one"],
            "documents": ["doc.c"],
        },
        "resolved_documents": ["doc.a", "doc.b", "doc.c"],
    }
    chunks = scoped_state["index"]["chunks"]
    assert [entry["document_id"] for entry in chunks] == ["doc.a", "doc.b", "doc.c"]
    assert sorted(scoped_state["ingestion"].keys()) == ["doc.a", "doc.b", "doc.c"]

    only_collection_state, only_collection_summary = apply_retrieval_scope(
        state=state,
        scope={"collections": ["kb.one"], "documents": []},
    )
    assert only_collection_summary["resolved_documents"] == ["doc.a", "doc.b"]
    assert [entry["document_id"] for entry in only_collection_state["index"]["chunks"]] == ["doc.a", "doc.b"]


def test_retrieval_service_respects_collection_scope_end_to_end() -> None:
    state: dict = {}
    first = run_ingestion_pipeline(
        state=state,
        content=b"Policy alpha source clause.",
        source_name="alpha.txt",
        source_identity="fixtures/alpha-scope.txt",
        source_type="upload",
        source_uri="upload://fixtures/alpha-scope.txt",
        mime_type="text/plain",
    )
    second = run_ingestion_pipeline(
        state=state,
        content=b"Policy beta source clause.",
        source_name="beta.txt",
        source_identity="fixtures/beta-scope.txt",
        source_type="upload",
        source_uri="upload://fixtures/beta-scope.txt",
        mime_type="text/plain",
    )
    first_doc_id = first["document"]["doc_id"]
    second_doc_id = second["document"]["doc_id"]

    upsert_collection_membership(
        state,
        collection_id="kb.alpha",
        document_id=first_doc_id,
        name="kb.alpha",
    )

    payload = run_retrieval_service(
        query="policy",
        state=state,
        project_root=None,
        app_path=None,
        retrieval_config={
            "top_k": 5,
            "filters": {"tags": []},
            "scope": {
                "collections": ["kb.alpha"],
                "documents": [],
            },
        },
    )

    assert payload["retrieval_scope"] == {
        "active": True,
        "requested": {
            "collections": ["kb.alpha"],
            "documents": [],
        },
        "resolved_documents": [first_doc_id],
    }
    rows = payload["retrieval_results"]
    assert rows
    assert all(row["doc_id"] == first_doc_id for row in rows)
    assert all(row["doc_id"] != second_doc_id for row in rows)

    unscoped = run_retrieval_service(
        query="policy",
        state=state,
        project_root=None,
        app_path=None,
        retrieval_config={
            "top_k": 5,
            "filters": {"tags": []},
            "scope": {
                "collections": [],
                "documents": [],
            },
        },
    )
    unscoped_doc_ids = sorted({row["doc_id"] for row in unscoped["retrieval_results"]})
    assert unscoped_doc_ids == sorted([first_doc_id, second_doc_id])


__all__ = []
