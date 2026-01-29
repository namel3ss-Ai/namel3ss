from __future__ import annotations

import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from namel3ss.beta_lock.repo_clean import repo_dirty_entries
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.backend.upload_handler import handle_upload
from namel3ss.runtime.backend.upload_recorder import UploadRecorder


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "fixtures"


def _ctx(tmp_path: Path, *, capabilities: tuple[str, ...] = ("uploads",)) -> SimpleNamespace:
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    return SimpleNamespace(
        capabilities=capabilities,
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
    )


def test_upload_progress_is_deterministic_and_monotonic(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    payload = b"a" * 200000
    response = handle_upload(
        ctx,
        headers={"Content-Type": "application/octet-stream"},
        rfile=io.BytesIO(payload),
        content_length=len(payload),
        upload_name="progress.bin",
    )
    progress_events = [event for event in response["traces"] if event.get("type") == "upload_progress"]
    expected = json.loads((FIXTURE_DIR / "upload_progress_golden.json").read_text(encoding="utf-8"))
    assert progress_events == expected
    bytes_received = [event["bytes_received"] for event in progress_events]
    assert bytes_received == sorted(bytes_received)
    percents = [event["percent_complete"] for event in progress_events if event.get("percent_complete") is not None]
    assert percents == sorted(percents)


def test_upload_preview_metadata_redacted(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    payload = b"alpha\nbeta"
    response = handle_upload(
        ctx,
        headers={"Content-Type": "text/plain"},
        rfile=io.BytesIO(payload),
        content_length=len(payload),
        upload_name="/Users/alice/report.txt",
    )
    preview = response["upload"]["preview"]
    assert preview["filename"] == "report.txt"
    assert "/Users" not in preview["filename"]
    assert preview["item_count"] == 2


def test_upload_error_state_surfaces(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    recorder = UploadRecorder()
    body = b"ZZ\r\n"
    with pytest.raises(Namel3ssError):
        handle_upload(
            ctx,
            headers={"Content-Type": "application/octet-stream", "Transfer-Encoding": "chunked"},
            rfile=io.BytesIO(body),
            content_length=None,
            upload_name="bad.bin",
            recorder=recorder,
        )
    upload = recorder.build_upload_payload()
    assert upload["state"] == "rejected"
    error = upload["error"]
    assert error["code"] == "upload_chunk_error"
    assert "retry" in error["recovery_actions"]


def test_upload_does_not_dirty_repo(tmp_path: Path) -> None:
    baseline = set(repo_dirty_entries(ROOT))
    ctx = _ctx(tmp_path)
    handle_upload(
        ctx,
        headers={"Content-Type": "application/octet-stream"},
        rfile=io.BytesIO(b"data"),
        content_length=4,
        upload_name="clean.bin",
    )
    assert set(repo_dirty_entries(ROOT)) == baseline
