from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

from namel3ss.config.model import AppConfig, IngestionConfig
from namel3ss.ingestion import fallback_handler
from namel3ss.ingestion.api import run_ingestion
from namel3ss.runtime.backend.upload_store import store_upload


def _ctx(tmp_path: Path) -> SimpleNamespace:
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\ncapabilities:\n  uploads\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    return SimpleNamespace(
        capabilities=("uploads",),
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
    )


def _store_upload(tmp_path: Path, payload: bytes, *, filename: str, content_type: str) -> dict:
    return store_upload(_ctx(tmp_path), filename=filename, content_type=content_type, stream=io.BytesIO(payload))


def test_pdf_block_runs_ocr_fallback_and_converts_to_warn(tmp_path: Path, monkeypatch) -> None:
    metadata = _store_upload(
        tmp_path,
        b"%PDF-1.4\n/Type /Page\n%%EOF\n",
        filename="scan.pdf",
        content_type="application/pdf",
    )
    real_extract_pages = fallback_handler.extract_pages

    def fake_extract_pages(content: bytes, *, detected: dict, mode: str) -> tuple[list[str], str]:
        if mode == "ocr" and detected.get("type") == "pdf":
            return (
                [
                    "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma "
                    "tau upsilon phi chi psi omega"
                ],
                "ocr",
            )
        return real_extract_pages(content, detected=detected, mode=mode)

    monkeypatch.setattr(fallback_handler, "extract_pages", fake_extract_pages)

    result = run_ingestion(
        upload_id=metadata["checksum"],
        mode=None,
        state={},
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
    )
    report = result["report"]

    assert report["status"] == "warn"
    assert report["fallback_used"] == "ocr"
    assert report["method_used"] == "ocr"
    assert {"text_too_short", "low_unique_tokens"}.issubset(set(report["reasons"]))
    assert [entry["code"] for entry in report["reason_details"]] == report["reasons"]
    assert result["chunks"]


def test_pdf_with_binary_markers_still_runs_ocr_fallback(tmp_path: Path, monkeypatch) -> None:
    metadata = _store_upload(
        tmp_path,
        b"%PDF-1.4\n/Type /Page\nstream\n\x00\x00\x00\nendstream\n%%EOF\n",
        filename="scan.pdf",
        content_type="application/pdf",
    )
    real_extract_pages = fallback_handler.extract_pages

    def fake_extract_pages(content: bytes, *, detected: dict, mode: str) -> tuple[list[str], str]:
        if mode == "ocr" and detected.get("type") == "pdf":
            return (
                [
                    "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma "
                    "tau upsilon phi chi psi omega"
                ],
                "ocr",
            )
        return real_extract_pages(content, detected=detected, mode=mode)

    monkeypatch.setattr(fallback_handler, "extract_pages", fake_extract_pages)

    result = run_ingestion(
        upload_id=metadata["checksum"],
        mode=None,
        state={},
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
    )
    report = result["report"]

    assert report["status"] == "warn"
    assert report["fallback_used"] == "ocr"
    assert "null_bytes" not in report["gate"]["probe"]["block_reasons"]
    assert result["chunks"]


def test_pdf_fallback_failure_adds_ocr_failed_reason(tmp_path: Path, monkeypatch) -> None:
    metadata = _store_upload(
        tmp_path,
        b"%PDF-1.4\n/Type /Page\n%%EOF\n",
        filename="scan.pdf",
        content_type="application/pdf",
    )
    real_extract_pages = fallback_handler.extract_pages

    def failing_extract_pages(content: bytes, *, detected: dict, mode: str) -> tuple[list[str], str]:
        if mode == "ocr" and detected.get("type") == "pdf":
            raise RuntimeError("ocr backend missing")
        return real_extract_pages(content, detected=detected, mode=mode)

    monkeypatch.setattr(fallback_handler, "extract_pages", failing_extract_pages)

    result = run_ingestion(
        upload_id=metadata["checksum"],
        mode=None,
        state={},
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
    )
    report = result["report"]

    assert report["status"] == "block"
    assert report["fallback_used"] == "ocr"
    assert "ocr_failed" in report["reasons"]
    assert "ocr_failed" in [entry["code"] for entry in report["reason_details"]]
    assert result["chunks"] == []


def test_non_pdf_upload_does_not_run_ocr_fallback(tmp_path: Path) -> None:
    metadata = _store_upload(
        tmp_path,
        b"tiny",
        filename="tiny.txt",
        content_type="text/plain",
    )
    result = run_ingestion(
        upload_id=metadata["checksum"],
        mode=None,
        state={},
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
    )
    report = result["report"]
    assert report["status"] == "block"
    assert "fallback_used" not in report


def test_ocr_fallback_is_idempotent(monkeypatch) -> None:
    call_count = 0

    def fake_extract_pages(content: bytes, *, detected: dict, mode: str) -> tuple[list[str], str]:
        nonlocal call_count
        call_count += 1
        return (["alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu"], "ocr")

    monkeypatch.setattr(fallback_handler, "extract_pages", fake_extract_pages)

    prepared = SimpleNamespace(
        enable_ocr_fallback=True,
        resolved_mode="primary",
        probe_blocked=False,
        detected={"type": "pdf"},
        status="block",
        reasons=["text_too_short"],
        fallback_attempted=False,
        fallback_used=None,
        content=b"",
        source_name="scan.pdf",
        validate_pages=lambda *, pages, detected, source_name: pages,
        join_pages=lambda pages: "\f".join(pages),
        pages=[""],
        normalized="",
        signals={},
        method_used="primary",
    )

    first = fallback_handler.maybe_run_ocr_fallback(prepared)
    second = fallback_handler.maybe_run_ocr_fallback(prepared)

    assert first is second
    assert call_count == 1
    assert prepared.fallback_used == "ocr"


def test_disable_ocr_fallback_restores_legacy_behavior(tmp_path: Path) -> None:
    metadata = _store_upload(
        tmp_path,
        b"%PDF-1.4\n/Type /Page\n%%EOF\n",
        filename="scan.pdf",
        content_type="application/pdf",
    )
    result = run_ingestion(
        upload_id=metadata["checksum"],
        mode=None,
        state={},
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
        config=AppConfig(ingestion=IngestionConfig(enable_ocr_fallback=False)),
    )
    report = result["report"]
    assert report["status"] == "block"
    assert "fallback_used" not in report


def test_disable_diagnostics_omits_reason_details(tmp_path: Path) -> None:
    metadata = _store_upload(
        tmp_path,
        b"tiny",
        filename="tiny.txt",
        content_type="text/plain",
    )
    result = run_ingestion(
        upload_id=metadata["checksum"],
        mode=None,
        state={},
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
        config=AppConfig(ingestion=IngestionConfig(enable_diagnostics=False)),
    )
    assert "reason_details" not in result["report"]
