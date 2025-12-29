import json
from pathlib import Path

from namel3ss.cli.main import main


APP_SOURCE = '''ai "assistant":
  provider is "openai"
  model is "gpt-4.1"

spec is "1.0"

flow "demo":
  ask ai "assistant" with input: "hi" as reply
  return reply
'''


def test_cli_loads_dotenv_for_check(monkeypatch, tmp_path):
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_SOURCE, encoding="utf-8")
    (tmp_path / ".env").write_text("NAMEL3SS_OPENAI_API_KEY=token\n", encoding="utf-8")

    class StubProvider:
        def ask(self, **kwargs):
            return type("Resp", (), {"output": "ok"})()

    def fake_get_provider(name, config):
        return StubProvider()

    monkeypatch.setattr("namel3ss.runtime.executor.ai_runner.get_provider", fake_get_provider)
    code = main([str(app_path), "ui"])
    assert code == 0
