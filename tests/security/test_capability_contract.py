from __future__ import annotations

import pytest

from namel3ss.runtime.capabilities.gates.base import CapabilityViolation, REASON_GUARANTEE_BLOCKED
from namel3ss.runtime.capabilities.gates.network_gate import check_network
from namel3ss.runtime.capabilities.gates.trace import record_capability_check
from namel3ss.runtime.capabilities.model import CapabilityContext, EffectiveGuarantees


def test_capability_denial_emits_trace_event() -> None:
    traces: list[dict[str, object]] = []
    guarantees = EffectiveGuarantees(no_network=True, sources={"no_network": "policy"})
    ctx = CapabilityContext(
        tool_name="demo",
        resolved_source="binding",
        runner="local",
        protocol_version=1,
        guarantees=guarantees,
    )

    def record(check) -> None:
        record_capability_check(ctx, check, traces)

    with pytest.raises(CapabilityViolation):
        check_network(ctx, record, url="https://example.com", method="get")

    assert traces
    event = traces[0]
    assert event.get("type") == "capability_check"
    assert event.get("capability") == "network"
    assert event.get("allowed") is False
    assert event.get("reason") == REASON_GUARANTEE_BLOCKED
    assert event.get("guarantee_source") == "policy"
    assert event.get("tool_name") == "demo"
