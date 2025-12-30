from __future__ import annotations

from pathlib import Path
import json

from namel3ss import contract as build_contract
from namel3ss.runtime.executor.api import execute_program_flow
from namel3ss.runtime.store.memory_store import MemoryStore

from examples.demos._shared import api_cache


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEATHER_APP = PROJECT_ROOT / "examples/demos/weather_dashboard/app.ai"
CURRENCY_APP = PROJECT_ROOT / "examples/demos/currency_converter/app.ai"
WEATHER_FIXTURE = PROJECT_ROOT / "examples/demos/weather_dashboard/fixtures/weather_brussels.json"
FX_FIXTURE = PROJECT_ROOT / "examples/demos/currency_converter/fixtures/fx_eur_usd.json"


def _load_program(app_path: Path):
    contract_obj = build_contract(app_path.read_text(encoding="utf-8"))
    setattr(contract_obj.program, "app_path", app_path)
    setattr(contract_obj.program, "project_root", PROJECT_ROOT)
    return contract_obj.program


def _fixture_updated_at(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    return str(data.get("last_updated"))


def test_weather_cache_preferred_on_failure(monkeypatch, tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.json"
    monkeypatch.setenv("N3_API_CACHE_PATH", str(cache_path))
    monkeypatch.setenv("WEATHER_API_KEY", "key")
    monkeypatch.setenv("WEATHER_API_SECONDARY_KEY", "key")
    monkeypatch.setenv("WEATHER_API_FORCE_FAIL", "1")

    now = api_cache.now_timestamp()
    entry = api_cache.set_response(
        "weather:brussels",
        {"days": [{"date": "2024-05-01", "condition": "Sunny", "temperature": 25}]},
        updated_ts=now,
    )

    program = _load_program(WEATHER_APP)
    store = MemoryStore()
    execute_program_flow(program, "get_forecast", store=store, input={"values": {"city": "Brussels"}})

    status_schema = next(record for record in program.records if record.name == "WeatherStatus")
    rows = store.list_records(status_schema)
    assert rows
    assert rows[-1]["source"] == "cache"
    assert rows[-1]["stale"] is False
    assert rows[-1]["last_updated"] == entry.updated_at


def test_weather_stale_cache_on_failure(monkeypatch, tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.json"
    monkeypatch.setenv("N3_API_CACHE_PATH", str(cache_path))
    monkeypatch.setenv("WEATHER_API_KEY", "key")
    monkeypatch.setenv("WEATHER_API_SECONDARY_KEY", "key")
    monkeypatch.setenv("WEATHER_API_FORCE_FAIL", "1")

    old_ts = api_cache.now_timestamp() - (30 * 60 + 5)
    entry = api_cache.set_response(
        "weather:brussels",
        {"days": [{"date": "2024-05-01", "condition": "Sunny", "temperature": 25}]},
        updated_ts=old_ts,
    )

    program = _load_program(WEATHER_APP)
    store = MemoryStore()
    execute_program_flow(program, "get_forecast", store=store, input={"values": {"city": "Brussels"}})

    status_schema = next(record for record in program.records if record.name == "WeatherStatus")
    rows = store.list_records(status_schema)
    assert rows
    assert rows[-1]["source"] == "cache"
    assert rows[-1]["stale"] is True
    assert rows[-1]["last_updated"] == entry.updated_at


def test_weather_fixture_used_when_cache_empty(monkeypatch, tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.json"
    monkeypatch.setenv("N3_API_CACHE_PATH", str(cache_path))
    monkeypatch.setenv("WEATHER_API_KEY", "key")
    monkeypatch.setenv("WEATHER_API_SECONDARY_KEY", "key")
    monkeypatch.setenv("WEATHER_API_FORCE_FAIL", "1")

    program = _load_program(WEATHER_APP)
    store = MemoryStore()
    execute_program_flow(program, "get_forecast", store=store, input={"values": {"city": "Brussels"}})

    status_schema = next(record for record in program.records if record.name == "WeatherStatus")
    rows = store.list_records(status_schema)
    assert rows
    assert rows[-1]["source"] == "fixture"
    assert rows[-1]["stale"] is False
    assert rows[-1]["last_updated"] == _fixture_updated_at(WEATHER_FIXTURE)


def test_fx_cache_preferred_on_failure(monkeypatch, tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.json"
    monkeypatch.setenv("N3_API_CACHE_PATH", str(cache_path))
    monkeypatch.setenv("FX_API_KEY", "key")
    monkeypatch.setenv("FX_API_SECONDARY_KEY", "key")
    monkeypatch.setenv("FX_API_FORCE_FAIL", "1")

    now = api_cache.now_timestamp()
    entry = api_cache.set_response(
        "fx:EUR:USD",
        {"pair": "EUR/USD", "rate": 1.11},
        updated_ts=now,
    )

    program = _load_program(CURRENCY_APP)
    store = MemoryStore()
    execute_program_flow(
        program,
        "convert",
        store=store,
        input={"values": {"from": "EUR", "to": "USD", "amount": 5}},
    )

    result_schema = next(record for record in program.records if record.name == "ConversionResult")
    rows = store.list_records(result_schema)
    assert rows
    assert rows[-1]["source"] == "cache"
    assert rows[-1]["stale"] is False
    assert rows[-1]["last_updated"] == entry.updated_at


def test_fx_fixture_used_when_cache_empty(monkeypatch, tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.json"
    monkeypatch.setenv("N3_API_CACHE_PATH", str(cache_path))
    monkeypatch.setenv("FX_API_KEY", "key")
    monkeypatch.setenv("FX_API_SECONDARY_KEY", "key")
    monkeypatch.setenv("FX_API_FORCE_FAIL", "1")

    program = _load_program(CURRENCY_APP)
    store = MemoryStore()
    execute_program_flow(
        program,
        "convert",
        store=store,
        input={"values": {"from": "EUR", "to": "USD", "amount": 5}},
    )

    result_schema = next(record for record in program.records if record.name == "ConversionResult")
    rows = store.list_records(result_schema)
    assert rows
    assert rows[-1]["source"] == "fixture"
    assert rows[-1]["stale"] is False
    assert rows[-1]["last_updated"] == _fixture_updated_at(FX_FIXTURE)
