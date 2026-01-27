from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

from namel3ss.ingestion.api import run_ingestion
from namel3ss.retrieval.api import run_retrieval
from namel3ss.runtime.backend.upload_store import store_upload
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.runtime.ui.actions import handle_action
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


def _ctx(tmp_path: Path, source: str | None = None) -> SimpleNamespace:
    app_path = tmp_path / "app.ai"
    content = source or 'spec is "1.0"\ncapabilities:\n  uploads\nflow "demo":\n  return "ok"\n'
    app_path.write_text(content, encoding="utf-8")
    return SimpleNamespace(
        capabilities=("uploads",),
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
    )


def _store_upload(
    tmp_path: Path,
    payload: bytes,
    *,
    filename: str,
    content_type: str,
    source: str | None = None,
) -> dict:
    ctx = _ctx(tmp_path, source)
    return store_upload(ctx, filename=filename, content_type=content_type, stream=io.BytesIO(payload))


def _store_text_upload(tmp_path: Path, payload: bytes, *, filename: str, source: str | None = None) -> dict:
    return _store_upload(tmp_path, payload, filename=filename, content_type="text/plain", source=source)


def _ingest(tmp_path: Path, state: dict, payload: bytes, *, filename: str, source: str | None = None) -> dict:
    metadata = _store_text_upload(tmp_path, payload, filename=filename, source=source)
    run_ingestion(
        upload_id=metadata["checksum"],
        mode=None,
        state=state,
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
    )
    return metadata


def _action_id(program, action_type: str) -> str:
    manifest = build_manifest(program, state={}, store=MemoryStore())
    for action_id, entry in manifest.get("actions", {}).items():
        if entry.get("type") == action_type:
            return action_id
    raise AssertionError(f"Action '{action_type}' not found in manifest")


def test_ingestion_review_action_is_deterministic(tmp_path: Path) -> None:
    source = '''
spec is "1.0"

capabilities:
  uploads

page "home":
  upload receipt
'''.lstrip()
    payload = b"Document at /Users/alice/report.txt with enough words to pass quality checks."
    state: dict = {}
    metadata = _ingest(tmp_path, state, payload, filename="review.txt", source=source)
    program = lower_ir_program(source)
    program.app_path = (tmp_path / "app.ai").as_posix()
    program.project_root = str(tmp_path)
    review_action = _action_id(program, "ingestion_review")
    first = handle_action(
        program,
        action_id=review_action,
        payload={"upload_id": metadata["checksum"]},
        state=state,
        store=MemoryStore(),
    )
    second = handle_action(
        program,
        action_id=review_action,
        payload={"upload_id": metadata["checksum"]},
        state=state,
        store=MemoryStore(),
    )
    assert first["result"] == second["result"]
    report = first["result"]["ingestion_review"]["reports"][0]
    assert list(report.keys()) == ["upload_id", "status", "method_used", "signals", "reasons", "preview"]
    assert "/Users" not in report["preview"]


def test_skip_and_reingest_updates_retrieval(tmp_path: Path) -> None:
    source = '''
spec is "1.0"

capabilities:
  uploads

page "home":
  upload receipt
'''.lstrip()
    line = "warning line with enough distinct words to keep ratios stable"
    payload = "\n".join([line, line, line, "unique line one", "unique line two"]).encode("utf-8")
    state: dict = {}
    metadata = _ingest(tmp_path, state, payload, filename="clean.txt", source=source)
    program = lower_ir_program(source)
    program.app_path = (tmp_path / "app.ai").as_posix()
    program.project_root = str(tmp_path)
    skip_action = _action_id(program, "ingestion_skip")
    run_action = _action_id(program, "ingestion_run")
    identity = {"permissions": ["ingestion.skip", "retrieval.include_warn"]}
    before = run_retrieval(
        query="warning",
        state=state,
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
        identity=identity,
    )
    assert before["results"]
    handle_action(
        program,
        action_id=skip_action,
        payload={"upload_id": metadata["checksum"]},
        state=state,
        store=MemoryStore(),
        identity=identity,
    )
    after_skip = run_retrieval(
        query="warning",
        state=state,
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
        identity=identity,
    )
    assert after_skip["results"] == []
    handle_action(
        program,
        action_id=run_action,
        payload={"upload_id": metadata["checksum"], "mode": "primary"},
        state=state,
        store=MemoryStore(),
        identity=identity,
    )
    after_run = run_retrieval(
        query="warning",
        state=state,
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
        identity=identity,
    )
    assert after_run["results"]


def test_ingestion_run_mode_is_respected(tmp_path: Path) -> None:
    source = '''
spec is "1.0"

capabilities:
  uploads

page "home":
  upload receipt
'''.lstrip()
    pdf_bytes = b"%PDF-1.4\n/Type /Page\n(Hello)\n"
    metadata = _store_upload(tmp_path, pdf_bytes, filename="sample.pdf", content_type="application/pdf", source=source)
    state: dict = {}
    program = lower_ir_program(source)
    program.app_path = (tmp_path / "app.ai").as_posix()
    program.project_root = str(tmp_path)
    run_action = _action_id(program, "ingestion_run")
    response = handle_action(
        program,
        action_id=run_action,
        payload={"upload_id": metadata["checksum"], "mode": "layout"},
        state=state,
        store=MemoryStore(),
        identity={"permissions": ["ingestion.override"]},
    )
    report = response["state"]["ingestion"][metadata["checksum"]]
    assert report["method_used"] == "layout"
