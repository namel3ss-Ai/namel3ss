import pytest

from namel3ss.secrets import collect_secret_values, redact_text


@pytest.mark.parametrize(
    "env_var",
    [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "MISTRAL_API_KEY",
        "HUGGINGFACE_API_KEY",
        "HUGGINGFACEHUB_API_TOKEN",
        "SPEECH_API_KEY",
        "THIRD_PARTY_APIS_KEY",
    ],
)
def test_alias_env_is_redacted(monkeypatch, env_var):
    secret_value = f"test-{env_var.lower()}-value"
    monkeypatch.setenv(env_var, secret_value)
    values = collect_secret_values()
    assert secret_value in values
    redacted = redact_text(f"token={secret_value}", values)
    assert secret_value not in redacted
