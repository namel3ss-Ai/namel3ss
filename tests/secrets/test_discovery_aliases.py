from pathlib import Path

import pytest

from namel3ss.config.model import AppConfig
from namel3ss.secrets.discovery import PROVIDER_ENV, discover_required_secrets
from tests.conftest import lower_ir_program


SOURCE_TEMPLATE = '''spec is "1.0"

ai "assistant":
  provider is "{provider}"
  model is "test-model"

flow "demo":
  return "ok"
'''


@pytest.mark.parametrize(
    "provider,alias",
    [
        ("openai", "OPENAI_API_KEY"),
        ("anthropic", "ANTHROPIC_API_KEY"),
        ("gemini", "GEMINI_API_KEY"),
        ("gemini", "GOOGLE_API_KEY"),
        ("mistral", "MISTRAL_API_KEY"),
    ],
)
def test_alias_env_marks_secret_available(tmp_path: Path, monkeypatch, provider: str, alias: str) -> None:
    source = SOURCE_TEMPLATE.format(provider=provider)
    program = lower_ir_program(source)
    app_path = tmp_path / "app.ai"
    app_path.write_text(source, encoding="utf-8")
    canonical = PROVIDER_ENV[provider]

    monkeypatch.delenv(canonical, raising=False)
    monkeypatch.delenv(alias, raising=False)
    monkeypatch.setenv(alias, "test-value")

    secrets = discover_required_secrets(program, AppConfig(), target="local", app_path=app_path)
    secret = next(item for item in secrets if item.name == canonical)
    assert secret.available is True
    assert secret.source == "env"


@pytest.mark.parametrize(
    "provider,alias",
    [
        ("openai", "OPENAI_API_KEY"),
        ("anthropic", "ANTHROPIC_API_KEY"),
        ("gemini", "GEMINI_API_KEY"),
        ("mistral", "MISTRAL_API_KEY"),
    ],
)
def test_alias_dotenv_marks_secret_available(tmp_path: Path, monkeypatch, provider: str, alias: str) -> None:
    source = SOURCE_TEMPLATE.format(provider=provider)
    program = lower_ir_program(source)
    app_path = tmp_path / "app.ai"
    app_path.write_text(source, encoding="utf-8")
    canonical = PROVIDER_ENV[provider]

    monkeypatch.delenv(canonical, raising=False)
    monkeypatch.delenv(alias, raising=False)
    (tmp_path / ".env").write_text(f"{alias}=dotenv-test\n", encoding="utf-8")

    secrets = discover_required_secrets(program, AppConfig(), target="local", app_path=app_path)
    secret = next(item for item in secrets if item.name == canonical)
    assert secret.available is True
    assert secret.source == "dotenv"
