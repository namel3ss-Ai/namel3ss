from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

from namel3ss.runtime.backend.upload_store import store_upload
from tests.conftest import run_flow

INGESTION_FIXTURE = Path("tests/fixtures/pipeline_ingestion.ai")
RETRIEVAL_FIXTURE = Path("tests/fixtures/pipeline_retrieval.ai")


def _store_text_upload(tmp_path: Path, app_path: Path, payload: bytes) -> dict:
    ctx = SimpleNamespace(project_root=str(tmp_path), app_path=app_path.as_posix())
    return store_upload(ctx, filename="notes.txt", content_type="text/plain", stream=io.BytesIO(payload))


def _write_app(tmp_path: Path, source: str) -> Path:
    app_path = tmp_path / "app.ai"
    app_path.write_text(source, encoding="utf-8")
    return app_path


def test_pipeline_ingestion_blocked_does_not_index(tmp_path: Path) -> None:
    source = INGESTION_FIXTURE.read_text(encoding="utf-8")
    app_path = _write_app(tmp_path, source)
    metadata = _store_text_upload(tmp_path, app_path, b"hi")

    result = run_flow(
        source,
        flow_name="ingest_only",
        input_data={"upload_id": metadata["checksum"]},
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
    )

    output = result.last_value
    assert isinstance(output, dict)
    report = output.get("report")
    assert isinstance(report, dict)
    assert report.get("status") == "block"

    index = output.get("index")
    if isinstance(index, dict):
        chunks = index.get("chunks") or []
        assert all(entry.get("upload_id") != metadata["checksum"] for entry in chunks if isinstance(entry, dict))
    else:
        assert index is None


def test_pipeline_ingestion_deterministic_index(tmp_path: Path) -> None:
    source = INGESTION_FIXTURE.read_text(encoding="utf-8")
    app_path = _write_app(tmp_path, source)
    payload = b"hello world with enough distinct words to pass the deterministic quality gate"
    metadata = _store_text_upload(tmp_path, app_path, payload)

    first = run_flow(
        source,
        flow_name="ingest_only",
        input_data={"upload_id": metadata["checksum"]},
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
    )
    second = run_flow(
        source,
        flow_name="ingest_only",
        input_data={"upload_id": metadata["checksum"]},
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
    )

    assert first.last_value == second.last_value
    output = first.last_value
    assert isinstance(output, dict)
    index = output.get("index")
    assert isinstance(index, dict)
    chunks = index.get("chunks")
    assert isinstance(chunks, list)
    assert chunks


def test_pipeline_retrieval_ordering_is_deterministic(tmp_path: Path) -> None:
    source = RETRIEVAL_FIXTURE.read_text(encoding="utf-8")
    app_path = _write_app(tmp_path, source)
    ingestion = {
        "u1": {"status": "pass"},
        "u2": {"status": "pass"},
    }
    index = {
        "chunks": [
            {"upload_id": "u1", "order": 0, "text": "invoice one"},
            {"upload_id": "u2", "order": 0, "text": "invoice two"},
        ]
    }

    result = run_flow(
        source,
        flow_name="retrieve_only",
        input_data={"query": "invoice", "ingestion": ingestion, "index": index},
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
    )

    output = result.last_value
    assert isinstance(output, dict)
    report = output.get("report")
    assert isinstance(report, dict)
    results = report.get("results")
    assert isinstance(results, list)
    assert [item.get("upload_id") for item in results] == ["u1", "u2"]


def test_pipeline_steps_are_deterministic_in_explain(tmp_path: Path) -> None:
    source = INGESTION_FIXTURE.read_text(encoding="utf-8")
    app_path = _write_app(tmp_path, source)
    payload = b"hello world with enough distinct words to pass the deterministic quality gate"
    metadata = _store_text_upload(tmp_path, app_path, payload)

    first = run_flow(
        source,
        flow_name="ingest_only",
        input_data={"upload_id": metadata["checksum"]},
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
    )
    second = run_flow(
        source,
        flow_name="ingest_only",
        input_data={"upload_id": metadata["checksum"]},
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
    )

    first_steps = [step for step in first.execution_steps if step.get("kind") == "pipeline_step"]
    second_steps = [step for step in second.execution_steps if step.get("kind") == "pipeline_step"]
    assert first_steps == second_steps
    assert len(first_steps) == 6

    for step in first_steps:
        data = step.get("data")
        assert isinstance(data, dict)
        assert data.get("pipeline") == "ingestion"
        assert data.get("step_id")
        assert data.get("step_kind")
        assert data.get("status")
        assert isinstance(data.get("summary"), dict)
        assert data.get("checksum")
        assert isinstance(data.get("step_ordinal"), int)
