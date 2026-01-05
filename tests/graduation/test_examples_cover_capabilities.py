from pathlib import Path

from namel3ss.graduation.capabilities import STATUS_SHIPPED, capabilities


def test_examples_cover_capabilities() -> None:
    for capability in capabilities():
        if capability.status != STATUS_SHIPPED:
            continue
        assert capability.tests, f"missing tests for {capability.id}"
        for path in capability.tests:
            assert Path(path).exists(), f"missing proof file {path}"
