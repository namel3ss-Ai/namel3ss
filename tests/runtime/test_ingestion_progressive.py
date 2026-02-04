from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

from namel3ss.ingestion.api import run_ingestion_progressive
from namel3ss.retrieval.api import run_retrieval
from namel3ss.runtime.backend.job_queue import run_job_queue
from namel3ss.runtime.backend.upload_store import store_upload


def _ctx(tmp_path: Path) -> SimpleNamespace:
    app_path = tmp_path / "app.ai"
    app_path.write_text(
        'spec is "1.0"\ncapabilities:\n  uploads\nflow "demo":\n  return "ok"\n',
        encoding="utf-8",
    )
    return SimpleNamespace(
        capabilities=("uploads",),
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
    )


def _job_ctx(tmp_path: Path, state: dict) -> SimpleNamespace:
    app_path = tmp_path / "app.ai"
    return SimpleNamespace(
        job_queue=[],
        job_enqueue_counter=0,
        traces=[],
        execution_steps=[],
        execution_step_counter=0,
        jobs={},
        job_order=[],
        observability=None,
        state=state,
        config=None,
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
    )


def _store_upload(tmp_path: Path, payload: bytes, *, filename: str) -> dict:
    ctx = _ctx(tmp_path)
    return store_upload(ctx, filename=filename, content_type="text/plain", stream=io.BytesIO(payload))


def test_progressive_ingestion_enqueues_deep_scan_and_updates_index(tmp_path: Path) -> None:
    payload = b"Paragraph one with enough words to pass the deterministic gate.\n\nParagraph two with more content."
    metadata = _store_upload(tmp_path, payload, filename="notes.txt")
    state: dict = {}
    job_ctx = _job_ctx(tmp_path, state)

    result = run_ingestion_progressive(
        upload_id=metadata["checksum"],
        mode=None,
        state=state,
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
        job_ctx=job_ctx,
    )

    assert result["status"] == "pass"
    assert result["chunks"]
    assert all(chunk.get("ingestion_phase") == "quick" for chunk in result["chunks"])
    assert len(job_ctx.job_queue) == 1

    retrieval = run_retrieval(
        query="paragraph",
        state=state,
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
    )
    assert retrieval["results"]

    run_job_queue(job_ctx)
    deep_entries = [
        entry
        for entry in state.get("index", {}).get("chunks", [])
        if entry.get("upload_id") == metadata["checksum"]
    ]
    assert deep_entries
    assert all(entry.get("ingestion_phase") == "deep" for entry in deep_entries)


def test_progress_events_are_deterministic(tmp_path: Path) -> None:
    payload = b"Alpha section with distinct words.\n\nBeta section with distinct words."
    metadata = _store_upload(tmp_path, payload, filename="progress.txt")

    first_state: dict = {}
    second_state: dict = {}
    first_job = _job_ctx(tmp_path, first_state)
    second_job = _job_ctx(tmp_path, second_state)

    first = run_ingestion_progressive(
        upload_id=metadata["checksum"],
        mode=None,
        state=first_state,
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
        job_ctx=first_job,
    )
    second = run_ingestion_progressive(
        upload_id=metadata["checksum"],
        mode=None,
        state=second_state,
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
        job_ctx=second_job,
    )

    assert first["progress"] == second["progress"]


def test_deep_scan_failure_preserves_quick_scan(tmp_path: Path) -> None:
    payload = (
        b"Stable content with enough distinct words to keep quality high and allow quick scan retrieval. "
        b"Additional unique terms ensure deterministic gating behavior."
    )
    metadata = _store_upload(tmp_path, payload, filename="fail.txt")
    state: dict = {}
    job_ctx = _job_ctx(tmp_path, state)

    result = run_ingestion_progressive(
        upload_id=metadata["checksum"],
        mode=None,
        state=state,
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
        job_ctx=job_ctx,
    )
    assert result["chunks"]

    # Remove the stored upload to force a deep scan failure.
    stored_path = metadata.get("stored_path", "")
    target = Path(str(tmp_path)) / ".namel3ss" / "files" / Path(str(stored_path))
    target.unlink(missing_ok=True)

    run_job_queue(job_ctx)
    report = state.get("ingestion", {}).get(metadata["checksum"], {})
    deep_phase = report.get("phases", {}).get("deep")
    assert deep_phase and deep_phase.get("status") == "failed"

    retrieval = run_retrieval(
        query="stable",
        state=state,
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
    )
    assert retrieval["results"]
