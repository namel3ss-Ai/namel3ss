from pathlib import Path

from namel3ss.studio import api


SOURCE = '''spec is "1.0"

ai "assistant":
  provider is "openai"
  model is "gpt-4.1"

flow "demo":
  return "ok"

page "home":
  button "Run":
    calls flow "demo"
'''


def test_secrets_payload_never_returns_values(tmp_path: Path, monkeypatch) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(SOURCE, encoding="utf-8")
    toml_path = tmp_path / "namel3ss.toml"
    toml_path.write_text('[persistence]\ntarget = "postgres"\n', encoding="utf-8")

    api_key = "sk-test-1234567890abcdefghijklmnopqrstuvwxyz"
    db_url = "postgres://user:pass@localhost/db"
    monkeypatch.setenv("NAMEL3SS_OPENAI_API_KEY", api_key)
    monkeypatch.setenv("N3_DATABASE_URL", db_url)

    payload = api.get_secrets_payload(SOURCE, str(app_path))
    assert payload["ok"] is True
    secrets = payload["secrets"]
    names = {item["name"] for item in secrets}
    assert "NAMEL3SS_OPENAI_API_KEY" in names
    assert "N3_DATABASE_URL" in names
    serialized = str(payload)
    assert api_key not in serialized
    assert db_url not in serialized
    for secret in secrets:
        assert set(secret.keys()) == {"name", "available", "source", "target"}
