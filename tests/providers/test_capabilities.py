import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.providers.capabilities import (
    ProviderCapabilities,
    get_provider_capabilities,
    list_known_providers,
)


def test_known_provider_capabilities():
    openai = get_provider_capabilities("openai")
    assert isinstance(openai, ProviderCapabilities)
    assert openai.supports_system_prompt is True
    assert openai.supports_tools is True
    assert openai.supports_json_mode is False
    assert openai.supports_streaming is False

    mock_cap = get_provider_capabilities("mock")
    assert mock_cap.supports_tools is True
    assert mock_cap.supports_system_prompt is True


def test_unknown_provider_is_rejected():
    with pytest.raises(Namel3ssError):
        get_provider_capabilities("unknown-provider")


def test_registry_names_are_stable():
    expected = {"mock", "ollama", "openai", "anthropic", "gemini", "mistral"}
    assert set(list_known_providers()) == expected
