from __future__ import annotations

from namel3ss.config.model import AppConfig, IngestionConfig
from namel3ss.ingestion.diagnostics import canonical_reason_codes, diagnostics_enabled, get_reason_details


def test_reason_details_are_ordered_and_mapped() -> None:
    details = get_reason_details(["low_unique_tokens", "text_too_short", "low_unique_tokens", "utf8_invalid"])
    assert [entry["code"] for entry in details] == ["utf8_invalid", "text_too_short", "low_unique_tokens"]
    assert details[1]["message"] == "Extracted text is too short for reliable indexing."
    assert details[2]["remediation"] == "Upload a clearer source file with richer text content."


def test_unknown_reason_code_uses_generic_guidance() -> None:
    details = get_reason_details(["custom_reason"])
    assert details == [
        {
            "code": "custom_reason",
            "message": "Ingestion reported an unknown reason code.",
            "remediation": "Review the upload, then re-run ingestion or replace the file.",
        }
    ]


def test_canonical_reason_codes_preserve_unknown_tail_order() -> None:
    ordered = canonical_reason_codes(["foo", "text_too_short", "bar", "foo", "low_unique_tokens"])
    assert ordered == ["text_too_short", "low_unique_tokens", "foo", "bar"]


def test_diagnostics_flag_defaults_to_enabled() -> None:
    assert diagnostics_enabled(None) is True
    config = AppConfig(ingestion=IngestionConfig(enable_diagnostics=False))
    assert diagnostics_enabled(config) is False
