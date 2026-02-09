from __future__ import annotations

from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


def _source() -> str:
    return '''
spec is "1.0"

page "home":
  upload receipt
'''.lstrip()


def _ingestion_detail(code: str, message: str, remediation: str) -> dict:
    return {
        "code": code,
        "message": message,
        "remediation": remediation,
    }


def test_manifest_injects_ingestion_status_after_upload() -> None:
    state = {
        "uploads": {
            "receipt": {
                "id": "upload-1",
                "name": "scan.pdf",
            }
        },
        "ingestion": {
            "upload-1": {
                "status": "warn",
                "reasons": ["empty_text", "low_unique_tokens"],
                "reason_details": [
                    _ingestion_detail(
                        "empty_text",
                        "No extractable text was found.",
                        "Run OCR or upload a PDF with embedded text.",
                    ),
                    _ingestion_detail(
                        "low_unique_tokens",
                        "Low number of unique tokens; content may be repetitive.",
                        "Upload a clearer source file with richer text content.",
                    ),
                ],
                "fallback_used": "ocr",
            }
        },
    }
    manifest = build_manifest(lower_ir_program(_source()), state=state, store=None)
    elements = manifest["pages"][0]["elements"]

    assert [entry.get("type") for entry in elements] == ["upload", "ingestion_status"]
    status = elements[1]
    assert status["status"] == "warn"
    assert status["reasons"] == ["low_unique_tokens", "empty_text"]
    assert status["details"] == [
        {
            "code": "low_unique_tokens",
            "message": "Low number of unique tokens; content may be repetitive.",
            "remediation": "Upload a clearer source file with richer text content.",
        },
        {
            "code": "empty_text",
            "message": "No extractable text was found.",
            "remediation": "Run OCR or upload a PDF with embedded text.",
        },
    ]
    assert status["source"] == "state.ingestion.upload-1"
    assert status["fallback_used"] == "ocr"


def test_manifest_skips_ingestion_status_without_report() -> None:
    state = {
        "uploads": {
            "receipt": {
                "id": "upload-1",
                "name": "scan.pdf",
            }
        }
    }
    manifest = build_manifest(lower_ir_program(_source()), state=state, store=None)
    elements = manifest["pages"][0]["elements"]
    assert [entry.get("type") for entry in elements] == ["upload"]


def test_manifest_selects_worst_upload_status_deterministically() -> None:
    state = {
        "uploads": {
            "receipt": {
                "a-upload": {"id": "a-upload", "name": "a.pdf"},
                "b-upload": {"id": "b-upload", "name": "b.pdf"},
            }
        },
        "ingestion": {
            "a-upload": {"status": "warn", "reasons": ["text_too_short"], "reason_details": []},
            "b-upload": {"status": "block", "reasons": ["empty_text"], "reason_details": []},
        },
    }
    manifest = build_manifest(lower_ir_program(_source()), state=state, store=None)
    status = manifest["pages"][0]["elements"][1]
    assert status["upload_id"] == "b-upload"
    assert status["status"] == "block"
