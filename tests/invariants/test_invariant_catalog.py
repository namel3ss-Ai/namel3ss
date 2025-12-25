from __future__ import annotations

import json
from pathlib import Path


def test_invariant_fixtures_exist() -> None:
    root = Path(__file__).resolve().parents[2]
    path = root / "resources" / "invariants_v1.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    invariants = data.get("invariants", [])
    assert invariants, "invariants_v1.json must list at least one invariant"
    for entry in invariants:
        for key in ("pass_fixture", "fail_fixture"):
            fixture = entry.get(key)
            assert fixture, f"Invariant {entry.get('id')} missing {key}"
            fixture_path = root / str(fixture)
            assert fixture_path.exists(), f"Missing fixture: {fixture_path}"
