from namel3ss.config.loader import load_config


def test_default_config_values(tmp_path):
    cfg = load_config(config_path=tmp_path / "config.json")
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
    cfg = load_config(config_path=tmp_path / "config.json")
    assert cfg.ollama.host == "http://example.com"
    assert cfg.ollama.timeout_seconds == 42


def test_file_overrides_defaults(tmp_path, monkeypatch):
    monkeypatch.delenv("NAMEL3SS_OLLAMA_HOST", raising=False)
    monkeypatch.delenv("NAMEL3SS_OLLAMA_TIMEOUT_SECONDS", raising=False)
    path = tmp_path / "config.json"
    path.write_text('{"ollama":{"host":"http://local", "timeout_seconds":55}}', encoding="utf-8")
    cfg = load_config(config_path=path)
    assert cfg.ollama.host == "http://local"
    assert cfg.ollama.timeout_seconds == 55
