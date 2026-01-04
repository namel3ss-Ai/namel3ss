from __future__ import annotations

import copy
import json
from pathlib import Path

from tests.golden.harness import _normalize_for_golden_compare


def test_golden_normalization_ignores_volatile_fields() -> None:
    snapshot_path = Path(__file__).resolve().parent / "snapshots" / "tool_basic" / "run.json"
    original = json.loads(snapshot_path.read_text(encoding="utf-8"))
    mutated = copy.deepcopy(original)
    _mutate_volatile_fields(mutated)
    assert _normalize_for_golden_compare(original) == _normalize_for_golden_compare(mutated)


def _mutate_volatile_fields(value: object) -> None:
    if isinstance(value, dict):
        if "python_path" in value:
            value["python_path"] = "/tmp/fake/python"
        if "duration_ms" in value:
            value["duration_ms"] = 123456
        if "trace_hash" in value:
            value["trace_hash"] = "deadbeef"
        for item in value.values():
            _mutate_volatile_fields(item)
        return
    if isinstance(value, list):
        for item in value:
            _mutate_volatile_fields(item)
