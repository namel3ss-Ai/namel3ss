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


def _store_text_upload(tmp_path: Path, payload: bytes, *, filename: str, source: str | None = None) -> dict:
    ctx = _ctx(tmp_path, source)
    return store_upload(ctx, filename=filename, content_type="text/plain", stream=io.BytesIO(payload))


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


def _retrieval_action_id(program) -> str:
    manifest = build_manifest(program, state={}, store=MemoryStore())
    for action_id, entry in manifest.get("actions", {}).items():
        if entry.get("type") == "retrieval_run":
            return action_id
    raise AssertionError("Retrieval action not found in manifest")


def test_blocked_uploads_return_no_results(tmp_path: Path) -> None:
    line = "repeat line with enough words to exceed limits"
    payload = "\n".join([line, line, line, line, "unique line"]).encode("utf-8")
    state: dict = {}
    _ingest(tmp_path, state, payload, filename="blocked.txt")
    result = run_retrieval(
        query="repeat",
        state=state,
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
    )
    assert result["results"] == []


def test_warn_only_when_no_pass(tmp_path: Path) -> None:
    pass_payload = (
        "clean line with distinct words to keep quality high and avoid repetition"
        " while still matching the line query"
    ).encode("utf-8")
    warn_line = "warning line with enough words to qualify for warning"
    warn_payload = "\n".join([warn_line, warn_line, warn_line, "unique one", "unique two"]).encode("utf-8")
    state: dict = {}
    pass_meta = _ingest(tmp_path, state, pass_payload, filename="pass.txt")
    warn_meta = _ingest(tmp_path, state, warn_payload, filename="warn.txt")

    result = run_retrieval(
        query="line",
        state=state,
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
    )
    assert result["included_warn"] is False
    assert result["results"]
    assert {item["upload_id"] for item in result["results"]} == {pass_meta["checksum"]}
    assert all(item["quality"] == "pass" for item in result["results"])

    warn_only = run_retrieval(
        query="warning",
        state=state,
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
    )
    assert warn_only["results"] == []
    allowed = run_retrieval(
        query="warning",
        state=state,
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
        identity={"permissions": ["retrieval.include_warn"]},
    )
    assert allowed["results"]
    assert {item["upload_id"] for item in allowed["results"]} == {warn_meta["checksum"]}
    assert all(item["quality"] == "warn" for item in allowed["results"])
    assert all(item["low_quality"] is True for item in allowed["results"])


def test_retrieval_order_is_stable(tmp_path: Path) -> None:
    state: dict = {}
    first = _ingest(
        tmp_path,
        state,
        b"alpha first content with enough words to pass quality checks",
        filename="first.txt",
    )
    second = _ingest(
        tmp_path,
        state,
        b"alpha second content with enough words to pass quality checks",
        filename="second.txt",
    )
    first_run = run_retrieval(
        query="alpha",
        state=state,
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
    )
    second_run = run_retrieval(
        query="alpha",
        state=state,
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
    )
    assert first_run == second_run
    order = [item["upload_id"] for item in first_run["results"]]
    assert order[0] == first["checksum"]
    assert second["checksum"] in order[1:]


def test_retrieval_metadata_and_scrubbing(tmp_path: Path) -> None:
    payload = b"Document at /Users/alice/report.txt and C:\\\\Users\\\\alice\\\\report.txt."
    state: dict = {}
    _ingest(tmp_path, state, payload, filename="paths.txt")
    result = run_retrieval(
        query="document",
        state=state,
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
    )
    assert result["results"]
    for item in result["results"]:
        assert item["quality"] in {"pass", "warn"}
        assert "upload_id" in item
        assert "chunk_id" in item
        assert "low_quality" in item
        assert "/Users" not in item["text"]
        assert "C:\\" not in item["text"]


def test_retrieval_action_runs(tmp_path: Path) -> None:
    source = '''
spec is "1.0"

capabilities:
  uploads

page "home":
  upload receipt
'''.lstrip()
    state: dict = {}
    _ingest(
        tmp_path,
        state,
        b"hello world with enough distinct words to pass the deterministic quality gate for retrieval",
        filename="hello.txt",
        source=source,
    )
    program = lower_ir_program(source)
    program.app_path = (tmp_path / "app.ai").as_posix()
    program.project_root = str(tmp_path)
    action_id = _retrieval_action_id(program)
    response = handle_action(
        program,
        action_id=action_id,
        payload={"query": "hello"},
        state=state,
        store=MemoryStore(),
    )
    retrieval = response["result"]["retrieval"]
    assert retrieval["results"]
