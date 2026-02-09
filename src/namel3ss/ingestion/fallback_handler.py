from __future__ import annotations

from types import SimpleNamespace

from namel3ss.config.model import AppConfig
from namel3ss.ingestion.diagnostics import canonical_reason_codes
from namel3ss.ingestion.extract import extract_pages
from namel3ss.ingestion.gate import gate_quality
from namel3ss.ingestion.normalize import normalize_text
from namel3ss.ingestion.signals import compute_signals

_OCR_TRIGGER_REASONS = frozenset({"text_too_short", "empty_text", "low_unique_tokens"})


def ocr_fallback_enabled(config: AppConfig | None) -> bool:
    if config is None:
        return True
    ingestion_cfg = getattr(config, "ingestion", None)
    value = getattr(ingestion_cfg, "enable_ocr_fallback", True)
    return bool(value)


def maybe_run_ocr_fallback(prepared: SimpleNamespace) -> SimpleNamespace:
    if not _should_run_ocr_fallback(prepared):
        return prepared

    original_reasons = list(prepared.reasons)
    prepared.fallback_used = "ocr"
    prepared.fallback_attempted = True

    try:
        pages, _ = extract_pages(prepared.content, detected=prepared.detected, mode="ocr")
        pages = prepared.validate_pages(
            pages=pages,
            detected=prepared.detected,
            source_name=prepared.source_name,
        )
        normalized = normalize_text(prepared.join_pages(pages))
        signals = compute_signals(normalized, detected=prepared.detected)
        quality_status, quality_reasons = gate_quality(signals)
    except Exception:
        prepared.status = "block"
        prepared.reasons = canonical_reason_codes([*original_reasons, "ocr_failed"])
        return prepared

    merged_reasons = canonical_reason_codes([*original_reasons, *quality_reasons])
    prepared.pages = pages
    prepared.normalized = normalized
    prepared.signals = signals
    prepared.reasons = merged_reasons

    if quality_status == "block":
        prepared.status = "block"
        return prepared

    prepared.status = "warn"
    prepared.method_used = "ocr"
    return prepared


def _should_run_ocr_fallback(prepared: SimpleNamespace) -> bool:
    if getattr(prepared, "fallback_attempted", False):
        return False
    if getattr(prepared, "fallback_used", None) == "ocr":
        return False
    if not bool(getattr(prepared, "enable_ocr_fallback", True)):
        return False
    if getattr(prepared, "resolved_mode", "primary") != "primary":
        return False
    if getattr(prepared, "probe_blocked", False):
        return False
    if str(getattr(prepared, "detected", {}).get("type") or "") != "pdf":
        return False
    if getattr(prepared, "status", "") != "block":
        return False
    reasons = {value for value in getattr(prepared, "reasons", []) if isinstance(value, str)}
    return bool(reasons & _OCR_TRIGGER_REASONS)


__all__ = ["maybe_run_ocr_fallback", "ocr_fallback_enabled"]
