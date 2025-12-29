from pathlib import Path

from namel3ss.graduation.capabilities import STATUS_SHIPPED, capabilities


def test_examples_cover_capabilities() -> None:
    for capability in capabilities():
        if capability.status != STATUS_SHIPPED:
            continue
        assert capability.tests, f"missing tests for {capability.id}"
        assert capability.examples, f"missing examples for {capability.id}"
        for path in capability.tests + capability.examples:
            assert Path(path).exists(), f"missing proof file {path}"
