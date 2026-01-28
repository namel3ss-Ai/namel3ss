from __future__ import annotations

import json
from pathlib import Path

from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.spec_freeze.v1.rules import HUMAN_TEXT_KEYS, has_bracket_chars
from tests.compute_core.helpers.samples import sample_sources
from tests.conftest import run_flow
from tests.spec_freeze.helpers.runtime_dump import dump_runtime


RUNTIME_GOLDEN_DIR = Path("tests/fixtures/compute_core/runtime")
FLOW_NAMES = {"compute_core": "core_demo"}


def test_compute_core_trace_bracketless() -> None:
    for name, _path, source in sample_sources():
        result = run_flow(
            source,
            flow_name=FLOW_NAMES[name],
            initial_state={},
            store=MemoryStore(),
            identity={"id": "user-1"},
        )
        actual = dump_runtime(result)
        fixture_path = RUNTIME_GOLDEN_DIR / f"{name}.json"
        expected = json.loads(fixture_path.read_text(encoding="utf-8"))

        _assert_no_brackets(actual)
        _assert_no_brackets(expected)


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
