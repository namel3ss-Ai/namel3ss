from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.config.model import AppConfig
from namel3ss.runtime.executor import execute_program_flow
from namel3ss.runtime.store.memory_store import MemoryStore


def _template_root() -> Path:
    return Path(__file__).resolve().parents[2] / "src" / "namel3ss" / "templates"


def test_template_flow_runs_in_memory_store():
    app_path = _template_root() / "operations_dashboard" / "app.ai"
    program, _ = load_program(str(app_path))
    store = MemoryStore()
    result = execute_program_flow(program, "create_sample_incident", store=store, input={}, config=AppConfig())
    assert result is not None
    schema = next(schema for schema in program.records if schema.name == "Incident")
    assert store.list_records(schema)
