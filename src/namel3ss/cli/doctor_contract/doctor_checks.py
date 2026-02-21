from __future__ import annotations

from typing import Any

from namel3ss.runtime.ingest.extractors.pdf_ocr_extractor import (
    OCR_NOT_AVAILABLE_ERROR_CODE,
    create_default_pdf_ocr_extractor,
)
from namel3ss.runtime.preview.preview_contract import (
    PREVIEW_UNION_CONTRACT_ERROR_CODE,
    build_preview_unavailable_payload,
    validate_preview_union_payload,
)
from namel3ss.studio.renderer_registry.registry_validator import (
    RendererRegistryValidationError,
    validate_renderer_registry,
)


def run_doctor_contract_checks() -> list[dict[str, Any]]:
    checks = [
        _renderer_registry_check(),
        _required_renderers_check(),
        _preview_union_check(),
        _ocr_capability_check(),
    ]
    return checks


def _renderer_registry_check() -> dict[str, Any]:
    try:
        validate_renderer_registry()
        return _check(
            check_id="contract_renderer_registry",
            status="ok",
            message="Renderer registry manifest is valid.",
            fix="No action needed.",
            code="contract.renderer_registry.ok",
            error_code=None,
        )
    except RendererRegistryValidationError as exc:
        return _check(
            check_id="contract_renderer_registry",
            status="error",
            message=f"Renderer registry validation failed: {exc}",
            fix="Run `python tools/build_renderer_manifest.py` and verify required renderer assets exist.",
            code="contract.renderer_registry.invalid",
            error_code=exc.error_code,
        )


def _required_renderers_check() -> dict[str, Any]:
    try:
        result = validate_renderer_registry()
        required = {"audit_viewer", "state_inspector"}
        missing = sorted(required - set(result.renderer_ids))
        if missing:
            return _check(
                check_id="contract_required_renderers",
                status="error",
                message=f"Required renderers missing: {', '.join(missing)}",
                fix="Regenerate renderer assets and ensure audit_viewer/state_inspector entrypoints are present.",
                code="contract.required_renderers.missing",
                error_code="N3E_RENDERER_REQUIRED_MISSING",
            )
        return _check(
            check_id="contract_required_renderers",
            status="ok",
            message="Required renderers are present.",
            fix="No action needed.",
            code="contract.required_renderers.ok",
            error_code=None,
        )
    except RendererRegistryValidationError as exc:
        return _check(
            check_id="contract_required_renderers",
            status="error",
            message=f"Required renderer check failed: {exc}",
            fix="Run `python tools/build_renderer_manifest.py`.",
            code="contract.required_renderers.invalid",
            error_code=exc.error_code,
        )


def _preview_union_check() -> dict[str, Any]:
    try:
        sample = build_preview_unavailable_payload(
            document_id="doctor-sample",
            page_number=1,
            reason_code="preview_unavailable",
            reason="Preview unavailable during contract check.",
        )
        validate_preview_union_payload(sample)
        return _check(
            check_id="contract_preview_union",
            status="ok",
            message="Preview union contract is valid.",
            fix="No action needed.",
            code="contract.preview_union.ok",
            error_code=None,
        )
    except Exception as exc:
        return _check(
            check_id="contract_preview_union",
            status="error",
            message=f"Preview union contract validation failed: {exc}",
            fix="Check runtime preview contract modules and rerun tests.",
            code="contract.preview_union.invalid",
            error_code=PREVIEW_UNION_CONTRACT_ERROR_CODE,
        )


def _ocr_capability_check() -> dict[str, Any]:
    extractor = create_default_pdf_ocr_extractor()
    if extractor.is_available():
        return _check(
            check_id="contract_ocr_capability",
            status="ok",
            message="OCR capability is available.",
            fix="No action needed.",
            code="contract.ocr.available",
            error_code=None,
        )
    return _check(
        check_id="contract_ocr_capability",
        status="warning",
        message="OCR capability is not available in this environment.",
        fix="Reinstall namel3ss so bundled OCR dependencies are available for scanned PDF extraction.",
        code="contract.ocr.unavailable",
        error_code=OCR_NOT_AVAILABLE_ERROR_CODE,
    )


def _check(
    *,
    check_id: str,
    status: str,
    message: str,
    fix: str,
    code: str,
    error_code: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "category": "studio",
        "code": code,
        "fix": fix,
        "id": check_id,
        "message": message,
        "status": status,
    }
    if error_code:
        payload["error_code"] = error_code
    return payload


__all__ = ["run_doctor_contract_checks"]
