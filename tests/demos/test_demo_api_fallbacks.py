from __future__ import annotations

from pathlib import Path

from namel3ss import contract as build_contract
from namel3ss.runtime.executor.api import execute_program_flow
from namel3ss.runtime.store.memory_store import MemoryStore


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEATHER_APP = PROJECT_ROOT / "examples/demos/weather_dashboard/app.ai"
CURRENCY_APP = PROJECT_ROOT / "examples/demos/currency_converter/app.ai"


def _load_program(app_path: Path):
    contract_obj = build_contract(app_path.read_text(encoding="utf-8"))
    setattr(contract_obj.program, "app_path", app_path)
    setattr(contract_obj.program, "project_root", PROJECT_ROOT)
    return contract_obj.program


def test_weather_fallback_uses_mock(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("N3_API_CACHE_PATH", str(tmp_path / "cache.json"))
    monkeypatch.setenv("WEATHER_API_KEY", "")
    monkeypatch.setenv("WEATHER_API_SECONDARY_KEY", "")
    program = _load_program(WEATHER_APP)
    store = MemoryStore()
    result = execute_program_flow(
        program,
        "get_forecast",
        store=store,
        input={"values": {"city": "Brussels"}},
    )
    assert result.state.get("error") is None
    status_schema = next(record for record in program.records if record.name == "WeatherStatus")
    rows = store.list_records(status_schema)
    assert rows
    assert rows[-1]["source"] == "mock"
    assert rows[-1]["stale"] is False


def test_currency_fallback_uses_mock(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("N3_API_CACHE_PATH", str(tmp_path / "cache.json"))
    monkeypatch.setenv("FX_API_KEY", "")
    monkeypatch.setenv("FX_API_SECONDARY_KEY", "")
    program = _load_program(CURRENCY_APP)
    store = MemoryStore()
    result = execute_program_flow(
        program,
        "convert",
        store=store,
        input={"values": {"from": "EUR", "to": "USD", "amount": 10}},
    )
    assert result.state.get("error") is None
    result_schema = next(record for record in program.records if record.name == "ConversionResult")
    rows = store.list_records(result_schema)
    assert rows
    assert rows[-1]["source"] == "mock"
    assert rows[-1]["stale"] is False
