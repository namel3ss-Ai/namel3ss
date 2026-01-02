from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.config.model import AppConfig
from namel3ss.runtime.executor import execute_program_flow
from namel3ss.runtime.store.memory_store import MemoryStore


def _template_root() -> Path:
    return Path(__file__).resolve().parents[2] / "src" / "namel3ss" / "templates"


def test_ai_assistant_runs_in_mock_mode(monkeypatch):
    app_path = _template_root() / "ai_assistant" / "app.ai"
    program, _ = load_program(str(app_path))
    store = MemoryStore()
    monkeypatch.delenv("NAMEL3SS_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("namel3ss.secrets.discovery.load_dotenv_for_path", lambda _: {})
    monkeypatch.setattr("namel3ss.config.dotenv.load_dotenv_for_path", lambda _: {})
    result = execute_program_flow(program, "ask_assistant", store=store, config=AppConfig())
    assert isinstance(result.last_value, str)
    status = result.state.get("status", {}).get("message") or ""
    assert "AI Mode: Mock" in status
