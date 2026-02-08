from __future__ import annotations

from namel3ss.spec_freeze.contracts.snapshot import build_snapshot


def test_snapshot_stable():
    first = build_snapshot()
    second = build_snapshot()
    assert first == second
