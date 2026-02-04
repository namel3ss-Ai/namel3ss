from __future__ import annotations

from namel3ss.retrieval.api import run_retrieval


def _state(chunks: list[dict]) -> dict:
    ingestion = {}
    for chunk in chunks:
        upload_id = chunk.get("upload_id")
        if isinstance(upload_id, str):
            ingestion[upload_id] = {"status": "pass"}
    return {"ingestion": ingestion, "index": {"chunks": chunks}}


def test_quick_only_when_deep_absent() -> None:
    chunks = [
        {
            "upload_id": "u1",
            "document_id": "u1",
            "source_name": "doc.txt",
            "page_number": 2,
            "chunk_index": 1,
            "ingestion_phase": "quick",
            "text": "alpha",
        },
        {
            "upload_id": "u1",
            "document_id": "u1",
            "source_name": "doc.txt",
            "page_number": 1,
            "chunk_index": 0,
            "ingestion_phase": "quick",
            "text": "beta",
        },
    ]
    result = run_retrieval(query=None, state=_state(chunks), project_root=None, app_path=None, tier="quick-only")
    assert [item["page_number"] for item in result["results"]] == [1, 2]
    assert all(item["ingestion_phase"] == "quick" for item in result["results"])


def test_deep_only_when_deep_exists() -> None:
    chunks = [
        {
            "upload_id": "u1",
            "document_id": "u1",
            "source_name": "doc.txt",
            "page_number": 1,
            "chunk_index": 1,
            "ingestion_phase": "quick",
            "text": "alpha",
        },
        {
            "upload_id": "u1",
            "document_id": "u1",
            "source_name": "doc.txt",
            "page_number": 1,
            "chunk_index": 0,
            "ingestion_phase": "deep",
            "text": "beta",
        },
    ]
    result = run_retrieval(query=None, state=_state(chunks), project_root=None, app_path=None, tier="deep-only")
    assert [item["ingestion_phase"] for item in result["results"]] == ["deep"]


def test_auto_merges_deep_then_quick_with_ordering() -> None:
    chunks = [
        {
            "upload_id": "u1",
            "document_id": "u1",
            "source_name": "doc.txt",
            "page_number": 3,
            "chunk_index": 0,
            "ingestion_phase": "quick",
            "text": "quick later",
        },
        {
            "upload_id": "u1",
            "document_id": "u1",
            "source_name": "doc.txt",
            "page_number": 1,
            "chunk_index": 1,
            "ingestion_phase": "deep",
            "text": "deep second",
        },
        {
            "upload_id": "u1",
            "document_id": "u1",
            "source_name": "doc.txt",
            "page_number": 1,
            "chunk_index": 0,
            "ingestion_phase": "deep",
            "text": "deep first",
        },
        {
            "upload_id": "u1",
            "document_id": "u1",
            "source_name": "doc.txt",
            "page_number": 2,
            "chunk_index": 0,
            "ingestion_phase": "quick",
            "text": "quick early",
        },
    ]
    state = _state(chunks)
    first = run_retrieval(query=None, state=state, project_root=None, app_path=None, tier="auto")
    second = run_retrieval(query=None, state=state, project_root=None, app_path=None, tier="auto")
    assert first == second
    ordered = [(item["ingestion_phase"], item["page_number"], item["chunk_index"]) for item in first["results"]]
    assert ordered == [
        ("deep", 1, 0),
        ("deep", 1, 1),
        ("quick", 2, 0),
        ("quick", 3, 0),
    ]
