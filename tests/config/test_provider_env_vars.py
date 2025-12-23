from namel3ss.config.loader import load_config


def test_provider_env_vars(monkeypatch, tmp_path):
    monkeypatch.setenv("NAMEL3SS_OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("NAMEL3SS_OPENAI_BASE_URL", "https://custom.openai.com")
    monkeypatch.setenv("NAMEL3SS_ANTHROPIC_API_KEY", "anthropic-key")
    monkeypatch.setenv("NAMEL3SS_GEMINI_API_KEY", "gemini-key")
    monkeypatch.setenv("NAMEL3SS_MISTRAL_API_KEY", "mistral-key")
    cfg = load_config(root=tmp_path)
    assert cfg.openai.api_key == "openai-key"
    assert cfg.openai.base_url == "https://custom.openai.com"
    assert cfg.anthropic.api_key == "anthropic-key"
    assert cfg.gemini.api_key == "gemini-key"
    assert cfg.mistral.api_key == "mistral-key"


def test_openai_base_url_default(monkeypatch, tmp_path):
    monkeypatch.delenv("NAMEL3SS_OPENAI_BASE_URL", raising=False)
    cfg = load_config(root=tmp_path)
    assert cfg.openai.base_url == "https://api.openai.com"
