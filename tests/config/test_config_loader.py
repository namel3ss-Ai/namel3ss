from namel3ss.config.loader import load_config


def test_default_config_values(tmp_path, monkeypatch):
    for key in [
        "NAMEL3SS_OPENAI_API_KEY",
        "NAMEL3SS_ANTHROPIC_API_KEY",
        "NAMEL3SS_GEMINI_API_KEY",
        "NAMEL3SS_MISTRAL_API_KEY",
        "NAMEL3SS_OPENAI_BASE_URL",
    ]:
        monkeypatch.delenv(key, raising=False)
    cfg = load_config(root=tmp_path)
    assert cfg.ollama.host == "http://127.0.0.1:11434"
    assert cfg.ollama.timeout_seconds == 30
    assert cfg.openai.base_url == "https://api.openai.com"
    assert cfg.openai.api_key is None
    assert cfg.anthropic.api_key is None
    assert cfg.gemini.api_key is None
    assert cfg.mistral.api_key is None


def test_env_overrides(monkeypatch, tmp_path):
    monkeypatch.setenv("NAMEL3SS_OLLAMA_HOST", "http://example.com")
    monkeypatch.setenv("NAMEL3SS_OLLAMA_TIMEOUT_SECONDS", "42")
    cfg = load_config(root=tmp_path)
    assert cfg.ollama.host == "http://example.com"
    assert cfg.ollama.timeout_seconds == 42


def test_file_overrides_defaults(tmp_path, monkeypatch):
    monkeypatch.delenv("NAMEL3SS_OLLAMA_HOST", raising=False)
    monkeypatch.delenv("NAMEL3SS_OLLAMA_TIMEOUT_SECONDS", raising=False)
    path = tmp_path / "namel3ss.toml"
    path.write_text('[ollama]\nhost = "http://local"\ntimeout_seconds = "55"\n', encoding="utf-8")
    cfg = load_config(root=tmp_path)
    assert cfg.ollama.host == "http://local"
    assert cfg.ollama.timeout_seconds == 55
