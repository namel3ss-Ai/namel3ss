from __future__ import annotations

import json

from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.spec_freeze.contracts.rules import RUNTIME_GOLDEN_DIR
from tests.conftest import run_flow
from tests.spec_freeze.helpers.runtime_dump import dump_runtime
from tests.spec_freeze.helpers.runtime_samples import runtime_sources


def test_runtime_golden():
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
        assert actual == expected, f"Runtime golden mismatch for {path}"
