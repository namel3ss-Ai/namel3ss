from __future__ import annotations

from namel3ss.cli.doctor_contract.doctor_command import append_contract_checks, contract_failure_codes


def test_append_contract_checks_adds_contract_entries() -> None:
    report = {"status": "ok", "checks": []}
    enriched = append_contract_checks(report)
    ids = [check["id"] for check in enriched["checks"]]
    assert "contract_renderer_registry" in ids
    assert "contract_preview_union" in ids
    assert "contract_required_renderers" in ids
    assert "contract_ocr_capability" in ids


def test_contract_failure_codes_only_include_contract_errors(monkeypatch) -> None:
    monkeypatch.setattr(
        "namel3ss.cli.doctor_contract.doctor_command.run_doctor_contract_checks",
        lambda: [
            {
                "id": "contract_renderer_registry",
                "category": "studio",
                "status": "error",
                "code": "contract.renderer_registry.invalid",
                "error_code": "N3E_RENDERER_REGISTRY_INVALID",
                "message": "broken",
                "fix": "fix",
            },
            {
                "id": "contract_ocr_capability",
                "category": "studio",
                "status": "warning",
                "code": "contract.ocr.unavailable",
                "error_code": "N3E_OCR_NOT_AVAILABLE",
                "message": "warn",
                "fix": "fix",
            },
        ],
    )
    report = append_contract_checks({"status": "ok", "checks": []})
    assert contract_failure_codes(report) == ["N3E_RENDERER_REGISTRY_INVALID"]
