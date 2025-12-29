from __future__ import annotations

import json

from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.spec_freeze.v1.rules import HUMAN_TEXT_KEYS, RUNTIME_GOLDEN_DIR, has_bracket_chars
from tests.conftest import run_flow
from tests.spec_freeze.helpers.runtime_dump import dump_runtime
from tests.spec_freeze.helpers.runtime_samples import runtime_sources


def test_trace_contracts():
    for name, path, flow_name, source in runtime_sources():
        result = run_flow(
            source,
            flow_name=flow_name,
            initial_state={},
            store=MemoryStore(),
            identity={"id": "user-1", "trust_level": "contributor"},
        )
        actual = dump_runtime(result)
        fixture_path = RUNTIME_GOLDEN_DIR / f"{name}.json"
        expected = json.loads(fixture_path.read_text(encoding="utf-8"))

        _assert_no_brackets(expected)
        _assert_no_brackets(actual)

        expected_events = _trace_events(expected)
        actual_events = _trace_events(actual)
        expected_types = {event.get("type") for event in expected_events if event.get("type")}
        actual_types = {event.get("type") for event in actual_events if event.get("type")}
        assert expected_types == actual_types, f"Trace event type mismatch for {path}"

        expected_keys = _event_keys_by_type(expected_events)
        actual_keys = _event_keys_by_type(actual_events)
        assert expected_keys == actual_keys, f"Trace event keys changed for {path}"


def _trace_events(payload: dict) -> list[dict]:
    events: list[dict] = []
    traces = payload.get("traces") or []
    for trace in traces:
        if not isinstance(trace, dict):
            continue
        canonical = trace.get("canonical_events")
        if isinstance(canonical, list):
            for event in canonical:
                if isinstance(event, dict):
                    events.append(event)
            continue
        if "type" in trace:
            events.append(trace)
    return events


def _event_keys_by_type(events: list[dict]) -> dict[str, set[str]]:
    keys_by_type: dict[str, set[str]] = {}
    for event in events:
        event_type = event.get("type")
        if not event_type:
            continue
        keys = set(event.keys())
        if event_type in keys_by_type:
            keys_by_type[event_type].update(keys)
        else:
            keys_by_type[event_type] = set(keys)
    return keys_by_type


def _assert_no_brackets(payload: dict) -> None:
    for text in _iter_human_text(payload):
        if has_bracket_chars(text):
            raise AssertionError(f"Bracket found in human text: {text}")


def _iter_human_text(value) -> list[str]:
    texts: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in HUMAN_TEXT_KEYS and isinstance(item, str):
                texts.append(item)
            texts.extend(_iter_human_text(item))
    elif isinstance(value, list):
        for item in value:
            texts.extend(_iter_human_text(item))
    return texts
