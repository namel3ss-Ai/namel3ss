from __future__ import annotations

from namel3ss.runtime.errors.classification import (
    RUNTIME_ERROR_CATEGORIES,
    build_runtime_error,
    classify_runtime_error,
)
from namel3ss.runtime.errors.normalize import attach_runtime_error_payload


def test_runtime_error_category_contract() -> None:
    assert RUNTIME_ERROR_CATEGORIES == (
        "server_unavailable",
        "auth_invalid",
        "auth_missing",
        "provider_misconfigured",
        "provider_mock_active",
        "action_denied",
        "policy_denied",
        "upload_failed",
        "ingestion_failed",
        "runtime_internal",
    )


def test_classification_server_unavailable() -> None:
    payload = classify_runtime_error(message="Failed to fetch", kind="runtime", status_code=None)
    assert payload["category"] == "server_unavailable"
    assert payload["origin"] == "network"


def test_classification_auth_invalid() -> None:
    payload = classify_runtime_error(message="Invalid token", kind="authentication", status_code=401)
    assert payload["category"] == "auth_invalid"


def test_classification_auth_missing() -> None:
    payload = classify_runtime_error(message="API token is required", kind="authentication")
    assert payload["category"] == "auth_missing"


def test_classification_provider_misconfigured() -> None:
    payload = classify_runtime_error(message="Missing NAMEL3SS_OPENAI_API_KEY", kind="provider")
    assert payload["category"] == "provider_misconfigured"


def test_classification_provider_mock_active() -> None:
    payload = classify_runtime_error(
        message="OpenAI key detected but provider is set to mock. Real AI calls are not active.",
        kind="runtime",
    )
    assert payload["category"] == "provider_mock_active"


def test_classification_policy_denied() -> None:
    payload = classify_runtime_error(
        message="Mutation blocked by policy.",
        kind="runtime",
        details={"category": "policy", "reason_code": "policy_denied"},
    )
    assert payload["category"] == "policy_denied"
    assert payload["stable_code"].endswith(".policy_denied")


def test_classification_action_denied() -> None:
    payload = classify_runtime_error(message="Action id is required", kind="engine")
    assert payload["category"] == "action_denied"


def test_classification_upload_failed() -> None:
    payload = classify_runtime_error(
        message="Unsupported upload file.",
        kind="runtime",
        endpoint="/api/upload",
    )
    assert payload["category"] == "upload_failed"


def test_classification_ingestion_failed() -> None:
    payload = classify_runtime_error(message="Ingestion report is missing.", kind="runtime")
    assert payload["category"] == "ingestion_failed"


def test_classification_runtime_internal_fallback() -> None:
    payload = classify_runtime_error(message="boom", kind="internal")
    assert payload["category"] == "runtime_internal"


def test_classification_is_deterministic() -> None:
    one = classify_runtime_error(message="Action id is required", kind="engine")
    two = classify_runtime_error(message="Action id is required", kind="engine")
    assert one == two


def test_attach_runtime_error_for_failed_payload() -> None:
    payload = {"ok": False, "kind": "engine", "error": "Action id is required"}
    normalized = attach_runtime_error_payload(payload, status_code=400, endpoint="/api/action")
    assert normalized["runtime_error"]["category"] == "action_denied"
    assert normalized["runtime_errors"][0]["stable_code"].startswith("runtime.action_denied")


def test_attach_runtime_error_with_diagnostics_on_success() -> None:
    response = {"ok": True, "result": "ok"}
    diagnostic = build_runtime_error(
        "provider_mock_active",
        stable_code="runtime.provider_mock_active.openai",
    )
    normalized = attach_runtime_error_payload(response, diagnostics=[diagnostic])
    assert normalized["ok"] is True
    assert normalized["degraded"] is True
    assert normalized["runtime_error"]["category"] == "provider_mock_active"
