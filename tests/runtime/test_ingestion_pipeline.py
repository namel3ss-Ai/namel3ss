from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

from namel3ss.ingestion.api import run_ingestion
from namel3ss.ingestion.chunk import chunk_text
from namel3ss.ingestion.gate import gate_quality
from namel3ss.ingestion.normalize import preview_text
from namel3ss.ingestion.signals import compute_signals
from namel3ss.runtime.backend.upload_store import store_upload
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.runtime.ui.actions import handle_action
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


def _ctx(tmp_path: Path, source: str | None = None) -> SimpleNamespace:
    app_path = tmp_path / "app.ai"
    content = source or 'spec is "1.0"\nflow "demo":\n  return "ok"\n'
    app_path.write_text(content, encoding="utf-8")
    return SimpleNamespace(
        capabilities=("uploads",),
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
    )


def _store_text_upload(tmp_path: Path, payload: bytes, *, filename: str, source: str | None = None) -> dict:
    ctx = _ctx(tmp_path, source)
    return store_upload(ctx, filename=filename, content_type="text/plain", stream=io.BytesIO(payload))


def test_signals_are_deterministic() -> None:
    text = "alpha beta\nalpha beta\n"
    signals = compute_signals(text, detected={})
    assert signals == {
        "text_chars": 22,
        "unique_token_ratio": 0.5,
        "non_ascii_ratio": 0.0,
        "line_break_ratio": 0.090909,
        "repeated_line_ratio": 1.0,
        "table_like_ratio": 0.0,
        "empty_pages_ratio": 0.0,
        "uppercase_alpha_ratio": 0.0,
        "vowel_alpha_ratio": 0.444444,
    }


def test_gate_blocks_repeated_lines() -> None:
    signals = {
        "text_chars": 120,
        "unique_token_ratio": 0.4,
        "non_ascii_ratio": 0.0,
        "line_break_ratio": 0.1,
        "repeated_line_ratio": 0.9,
        "table_like_ratio": 0.0,
        "empty_pages_ratio": 0.0,
    }
    status, reasons = gate_quality(signals)
    assert status == "block"
    assert "repeated_lines" in reasons


def test_gate_blocks_unreadable_text_pattern() -> None:
    signals = {
        "text_chars": 180,
        "unique_token_ratio": 0.9,
        "non_ascii_ratio": 0.0,
        "line_break_ratio": 0.0,
        "repeated_line_ratio": 0.0,
        "table_like_ratio": 0.0,
        "empty_pages_ratio": 0.0,
        "uppercase_alpha_ratio": 1.0,
        "vowel_alpha_ratio": 0.16,
    }
    status, reasons = gate_quality(signals)
    assert status == "block"
    assert "unreadable_text_pattern" in reasons


def test_unreadable_ciphertext_upload_is_blocked(tmp_path: Path) -> None:
    payload = (
        b"%XLOGLQJ D 3U RIHVLRQDO *UDGH &XVWRPHU VXSSRUW &KDW $SS ZLWK QDPHO3VV "
        b",QWURGXFWLRQ 7KH QDPHO3VV IUDPHZRUN DOORZV XV WR EXLOG $, GULYHQ DSSV "
        b"XVLQJ D VLQJOH GHWHUPLQLVWLF ODQJXDJH"
    )
    metadata = _store_text_upload(tmp_path, payload, filename="cipher.txt")
    state: dict = {}
    result = run_ingestion(
        upload_id=metadata["checksum"],
        mode=None,
        state=state,
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
    )
    assert result["status"] == "block"
    assert "unreadable_text_pattern" in result["report"]["reasons"]


def test_blocked_uploads_do_not_index(tmp_path: Path) -> None:
    line = "repeat line with enough words to exceed limits"
    payload = "\n".join([line, line, line, line, "unique line"]).encode("utf-8")
    metadata = _store_text_upload(tmp_path, payload, filename="blocked.txt")
    state: dict = {}
    result = run_ingestion(
        upload_id=metadata["checksum"],
        mode=None,
        state=state,
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
    )
    assert result["status"] == "block"
    chunks = state.get("index", {}).get("chunks", [])
    assert not [entry for entry in chunks if entry.get("upload_id") == metadata["checksum"]]


def test_warn_uploads_index_as_low_quality(tmp_path: Path) -> None:
    line = "repeat line with enough words for warning"
    payload = "\n".join([line, line, "unique line with other words"]).encode("utf-8")
    metadata = _store_text_upload(tmp_path, payload, filename="warn.txt")
    state: dict = {}
    result = run_ingestion(
        upload_id=metadata["checksum"],
        mode=None,
        state=state,
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
    )
    assert result["status"] == "warn"
    chunks = state.get("index", {}).get("chunks", [])
    entries = [entry for entry in chunks if entry.get("upload_id") == metadata["checksum"]]
    assert entries
    assert all(entry.get("low_quality") is True for entry in entries)


def test_chunk_order_is_stable() -> None:
    text = "para one.\n\npara two.\n\npara three."
    first = chunk_text(text, max_chars=10, overlap=2)
    second = chunk_text(text, max_chars=10, overlap=2)
    assert first == second
    assert [chunk["chunk_index"] for chunk in first] == list(range(len(first)))


def test_preview_scrubs_paths() -> None:
    raw = "See /Users/alice/report.txt and C:\\\\Users\\\\alice\\\\report.txt."
    preview = preview_text(raw, project_root="/Users/alice", app_path="/Users/alice/app.ai")
    assert "/Users" not in preview
    assert "C:\\" not in preview


def test_index_scrubs_paths(tmp_path: Path) -> None:
    payload = b"Document at /Users/alice/report.txt with safe content."
    metadata = _store_text_upload(tmp_path, payload, filename="paths.txt")
    state: dict = {}
    run_ingestion(
        upload_id=metadata["checksum"],
        mode=None,
        state=state,
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
    )
    chunks = state.get("index", {}).get("chunks", [])
    assert chunks
    texts = [entry.get("text", "") for entry in chunks]
    assert all("/Users" not in text for text in texts)


def test_pdf_fallback_uses_layout(tmp_path: Path) -> None:
    pdf_bytes = b"%PDF-1.4\n/Type /Page\n"
    metadata = store_upload(
        _ctx(tmp_path),
        filename="sample.pdf",
        content_type="application/pdf",
        stream=io.BytesIO(pdf_bytes),
    )
    state: dict = {}
    result = run_ingestion(
        upload_id=metadata["checksum"],
        mode=None,
        state=state,
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
    )
    report = result["report"]
    assert report["method_used"] == "layout"


def test_ingestion_action_runs(tmp_path: Path) -> None:
    source = '''
spec is "1.0"

capabilities:
  uploads

page "home":
  upload receipt
'''.lstrip()
    metadata = _store_text_upload(tmp_path, b"hello world", filename="hello.txt", source=source)
    program = lower_ir_program(source)
    program.app_path = (tmp_path / "app.ai").as_posix()
    program.project_root = str(tmp_path)
    manifest = build_manifest(program, state={}, store=None)
    ingestion_action = next(
        action_id
        for action_id, entry in manifest.get("actions", {}).items()
        if entry.get("type") == "ingestion_run"
    )
    response = handle_action(
        program,
        action_id=ingestion_action,
        payload={"upload_id": metadata["checksum"]},
        state={},
        store=MemoryStore(),
    )
    report = response["state"]["ingestion"][metadata["checksum"]]
    assert report["upload_id"] == metadata["checksum"]
