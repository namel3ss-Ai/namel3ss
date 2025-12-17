from namel3ss.config.model import AppConfig
from namel3ss.runtime.ai.providers.registry import get_provider


def test_registry_returns_providers():
    cfg = AppConfig()
    cfg.openai.api_key = "key"
    cfg.anthropic.api_key = "key"
    cfg.gemini.api_key = "key"
    cfg.mistral.api_key = "key"
    assert get_provider("openai", cfg).__class__.__name__ == "OpenAIProvider"
    assert get_provider("anthropic", cfg).__class__.__name__ == "AnthropicProvider"
    assert get_provider("gemini", cfg).__class__.__name__ == "GeminiProvider"
    assert get_provider("mistral", cfg).__class__.__name__ == "MistralProvider"
