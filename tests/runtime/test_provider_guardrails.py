from __future__ import annotations

from namel3ss.config.model import AppConfig
from namel3ss.runtime.providers.guardrails import provider_guardrail_diagnostics


def test_provider_mock_active_when_real_key_is_present() -> None:
    config = AppConfig()
    config.answer.provider = "mock"
    config.openai.api_key = "sk-test-value"
    diagnostics = provider_guardrail_diagnostics(config)
    assert diagnostics
    assert diagnostics[0]["category"] == "provider_mock_active"
    assert "provider is set to mock" in diagnostics[0]["message"]
    assert "sk-test-value" not in diagnostics[0]["message"]


def test_provider_misconfigured_when_selected_provider_has_no_key() -> None:
    config = AppConfig()
    config.answer.provider = "openai"
    config.openai.api_key = None
    diagnostics = provider_guardrail_diagnostics(config, env={})
    assert diagnostics
    entry = diagnostics[0]
    assert entry["category"] == "provider_misconfigured"
    assert entry["stable_code"] == "runtime.provider_misconfigured.openai.missing_key"


def test_provider_guardrails_empty_when_provider_is_configured() -> None:
    config = AppConfig()
    config.answer.provider = "openai"
    config.openai.api_key = "test-key"
    diagnostics = provider_guardrail_diagnostics(config, env={})
    assert diagnostics == []


def test_provider_guardrails_unknown_provider_is_deterministic() -> None:
    config = AppConfig()
    config.answer.provider = "unknown_provider"
    one = provider_guardrail_diagnostics(config, env={})
    two = provider_guardrail_diagnostics(config, env={})
    assert one == two
    assert one[0]["category"] == "provider_misconfigured"
    assert one[0]["stable_code"] == "runtime.provider_misconfigured.unknown_provider"
