from __future__ import annotations

import io
import json
from pathlib import Path
from types import SimpleNamespace

from namel3ss.ingestion.api import run_ingestion
from namel3ss.ingestion.gate_contract import EVIDENCE_EXCERPT_LIMIT
from namel3ss.runtime.backend.upload_store import store_upload
from namel3ss.runtime.persistence_paths import resolve_persistence_root

FIXTURE_DIR = Path("tests/fixtures/ingestion_gate")


def _ctx(tmp_path: Path) -> SimpleNamespace:
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\ncapabilities:\n  uploads\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    return SimpleNamespace(
        capabilities=("uploads",),
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
    )


def _store_upload(tmp_path: Path, payload: bytes, *, filename: str, content_type: str = "text/plain") -> dict:
    ctx = _ctx(tmp_path)
    return store_upload(ctx, filename=filename, content_type=content_type, stream=io.BytesIO(payload))


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_gate_decision_matches_fixture(tmp_path: Path) -> None:
    payload = (FIXTURE_DIR / "valid.txt").read_bytes()
    metadata = _store_upload(tmp_path, payload, filename="valid.txt")
    result = run_ingestion(
        upload_id=metadata["checksum"],
        mode=None,
        state={},
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
    )
    gate = result["report"]["gate"]
    expected = _load_json(FIXTURE_DIR / "valid_gate.json")
    assert gate == expected


def test_gate_blocks_null_bytes_and_writes_quarantine(tmp_path: Path) -> None:
    payload = (FIXTURE_DIR / "cracked_null.bin").read_bytes()
    metadata = _store_upload(tmp_path, payload, filename="cracked_null.bin", content_type="application/octet-stream")
    result = run_ingestion(
        upload_id=metadata["checksum"],
        mode=None,
        state={},
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
    )
    gate = result["report"]["gate"]
    assert gate.get("status") == "blocked"
    assert "null_bytes" in gate.get("probe", {}).get("block_reasons", [])
    quarantine_key = gate.get("quarantine", {}).get("key") or gate.get("cache", {}).get("key")
    root = resolve_persistence_root(str(tmp_path), (tmp_path / "app.ai").as_posix(), allow_create=False)
    assert root is not None
    quarantine_path = root / ".namel3ss" / "ingestion" / "quarantine" / f"{quarantine_key}.json"
    assert quarantine_path.exists()
    expected = _load_json(FIXTURE_DIR / "null_quarantine.json")
    actual = _load_json(quarantine_path)
    assert actual == expected


def test_gate_cache_hit_is_deterministic(tmp_path: Path) -> None:
    payload = (FIXTURE_DIR / "valid.txt").read_bytes()
    metadata = _store_upload(tmp_path, payload, filename="valid.txt")
    first = run_ingestion(
        upload_id=metadata["checksum"],
        mode=None,
        state={},
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
    )
    second = run_ingestion(
        upload_id=metadata["checksum"],
        mode=None,
        state={},
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
    )
    first_gate = first["report"]["gate"]
    second_gate = second["report"]["gate"]
    assert first_gate["cache"]["hit"] is False
    assert second_gate["cache"]["hit"] is False
    assert first_gate == second_gate
    cache_key = first_gate.get("cache", {}).get("key")
    root = resolve_persistence_root(str(tmp_path), (tmp_path / "app.ai").as_posix(), allow_create=False)
    assert root is not None
    cache_path = root / ".namel3ss" / "ingestion" / "cache" / f"{cache_key}.json"
    assert cache_path.exists()


def test_gate_evidence_is_redacted_and_bounded(tmp_path: Path) -> None:
    payload = (FIXTURE_DIR / "redact.txt").read_bytes()
    metadata = _store_upload(tmp_path, payload, filename="redact.txt")
    result = run_ingestion(
        upload_id=metadata["checksum"],
        mode=None,
        state={},
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
        secret_values=["SECRET_TOKEN"],
    )
    gate = result["report"]["gate"]
    excerpt = gate.get("evidence", {}).get("excerpt")
    assert isinstance(excerpt, str)
    assert "SECRET_TOKEN" not in excerpt
    assert "/Users/" not in excerpt
    assert len(excerpt) <= EVIDENCE_EXCERPT_LIMIT
