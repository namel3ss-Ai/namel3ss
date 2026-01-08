import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


SUMMARY_SOURCE = '''record "Metric":
  name text
  value number

page "home":
  table is "Metric"
  chart is "Metric"
'''


BAR_SOURCE = '''record "Metric":
  name text
  value number

page "home":
  table is "Metric"
  chart is "Metric":
    type is bar
    x is name
    y is value
    explain is "Value by name"
'''


MISSING_MAPPING_SOURCE = '''record "Flag":
  active boolean

page "home":
  table is "Flag"
  chart is "Flag":
    type is bar
'''


STATE_SOURCE = '''record "Metric":
  name text
  value number

page "home":
  table is "Metric"
  chart from is state.metric:
    type is bar
    x is name
    y is value
'''


def _load_record(program, name: str):
    return next(record for record in program.records if record.name == name)


def test_chart_summary_defaults_and_explain():
    program = lower_ir_program(SUMMARY_SOURCE)
    store = MemoryStore()
    record = _load_record(program, "Metric")
    store.save(record, {"name": "Alpha", "value": 10})
    store.save(record, {"name": "Beta", "value": 30})
    manifest = build_manifest(program, state={}, store=store)
    assert manifest == build_manifest(program, state={}, store=store)
    chart = next(el for el in manifest["pages"][0]["elements"] if el["type"] == "chart")
    assert chart["chart_type"] == "summary"
    assert chart["y"] == "value"
    assert chart["summary"]["count"] == 2
    assert chart["summary"]["total"] == 40
    assert chart["summary"]["average"] == pytest.approx(20)
    assert chart["explain"] == "Summary of Metric for value."


def test_chart_series_bar_is_deterministic():
    program = lower_ir_program(BAR_SOURCE)
    store = MemoryStore()
    record = _load_record(program, "Metric")
    store.save(record, {"name": "Alpha", "value": 5})
    store.save(record, {"name": "Beta", "value": 12})
    manifest = build_manifest(program, state={}, store=store)
    chart = next(el for el in manifest["pages"][0]["elements"] if el["type"] == "chart")
    assert chart["chart_type"] == "bar"
    assert chart["explain"] == "Value by name"
    assert chart["series"] == [{"x": "Alpha", "y": 5}, {"x": "Beta", "y": 12}]


def test_chart_requires_mapping_for_bar():
    program = lower_ir_program(MISSING_MAPPING_SOURCE)
    store = MemoryStore()
    with pytest.raises(Namel3ssError) as exc:
        build_manifest(program, state={}, store=store)
    assert "requires x and y" in str(exc.value).lower()


def test_chart_state_source_series():
    program = lower_ir_program(STATE_SOURCE)
    store = MemoryStore()
    state = {
        "metric": [
            {"name": "Alpha", "value": 2},
            {"name": "Beta", "value": 7},
        ]
    }
    manifest = build_manifest(program, state=state, store=store)
    chart = next(el for el in manifest["pages"][0]["elements"] if el["type"] == "chart")
    assert chart["source"] == "state.metric"
    assert chart["series"] == [{"x": "Alpha", "y": 2}, {"x": "Beta", "y": 7}]
