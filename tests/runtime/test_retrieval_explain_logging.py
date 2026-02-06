from __future__ import annotations

import io
import json
from pathlib import Path
from types import SimpleNamespace

from namel3ss.runtime.backend.upload_store import store_upload
from namel3ss.runtime.composition.retrieval_explain_logging import (
    build_retrieval_explain_metadata,
)
from tests.conftest import run_flow


def test_build_retrieval_explain_metadata_includes_candidates_scores_and_modalities() -> None:
    report = {
        "preferred_quality": "pass",
        "warn_policy": {"action": "retrieval.include_warn", "decision": "allowed"},
        "results": [
            {
                "document_id": "img-doc",
                "chunk_id": "img-doc:0",
                "page_number": 1,
                "keyword_overlap": 3,
                "source_name": "photo.png",
            },
            {
                "document_id": "aud-doc",
                "chunk_id": "aud-doc:0",
                "page_number": 1,
                "keyword_overlap": 2,
                "source_name": "voice.wav",
            },
        ],
        "explain": {
            "candidates": [
                {
                    "chunk_id": "img-doc:0",
                    "page_number": 1,
                    "keyword_overlap": 3,
                    "vector_score": 0.8,
                    "decision": "selected",
                    "reason": "top_k",
                },
                {
                    "chunk_id": "aud-doc:0",
                    "page_number": 1,
                    "keyword_overlap": 2,
                    "vector_score": 0.6,
                    "decision": "selected",
                    "reason": "top_k",
                },
            ]
        },
    }

    first = build_retrieval_explain_metadata(report)
    second = build_retrieval_explain_metadata(report)
    assert first == second
    assert first["modality"] == "mixed"
    assert first["selected"][0]["modality"] == "image"
    assert first["selected"][1]["modality"] == "audio"
    assert first["candidate_chunks"][0]["chunk_id"] == "img-doc:0"
    assert first["scores"][0]["score"] == 0.8


def test_retrieval_stage_logs_enriched_metadata_deterministically(tmp_path: Path) -> None:
    source = '''spec is "1.0"

capabilities:
  uploads

flow "demo":
  let ingestion_out is call pipeline "ingestion":
    input:
      upload_id is input.upload_id
    output:
      report
      ingestion
      index
  let retrieval_out is call pipeline "retrieval":
    input:
      query is input.query
    output:
      report
  return retrieval_out
'''
    app_path = tmp_path / "app.ai"
    app_path.write_text(source, encoding="utf-8")

    ctx = SimpleNamespace(project_root=str(tmp_path), app_path=app_path.as_posix())
    upload = store_upload(
        ctx,
        filename="notes.txt",
        content_type="text/plain",
        stream=io.BytesIO(
            b"deterministic retrieval text with enough unique words for indexing and explain metadata"
        ),
    )
    input_payload = {"upload_id": upload["checksum"], "query": "deterministic retrieval"}

    first = run_flow(
        source,
        flow_name="demo",
        input_data=input_payload,
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
    )
    second = run_flow(
        source,
        flow_name="demo",
        input_data=input_payload,
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
    )
    assert first.last_value == second.last_value

    explain_path = tmp_path / ".namel3ss" / "explain" / "last_explain.json"
    payload = json.loads(explain_path.read_text(encoding="utf-8"))
    retrieval_entries = [
        entry
        for entry in payload.get("entries", [])
        if entry.get("stage") == "retrieval" and entry.get("event_type") == "selected_chunks"
    ]
    assert retrieval_entries
    metadata = retrieval_entries[-1]["metadata"]
    assert metadata["candidate_chunks"]
    assert metadata["scores"]
    assert metadata["selected"]
    assert metadata["modality"] in {"text", "image", "audio", "mixed"}

