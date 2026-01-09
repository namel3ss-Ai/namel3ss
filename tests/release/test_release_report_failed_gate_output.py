from __future__ import annotations

from namel3ss.release.model import GateSpec
from namel3ss.release.runner import GateExecution, build_release_report


def test_release_report_includes_failed_gate_output() -> None:
    gate = GateSpec(name="Failing Gate", tests=(), required=True, command=("false",))

    def executor(_gate: GateSpec, _tests: tuple[str, ...], _fast: bool) -> GateExecution:
        return GateExecution(
            exit_code=1,
            duration_ms=12,
            command=_gate.command or (),
            stdout="gate stdout",
            stderr="gate stderr",
        )

    report = build_release_report(gates=(gate,), executor=executor, fast=True)
    payload = report.as_dict()
    details = payload["gates"][0]["details"]
    assert details["stdout_tail"] == "gate stdout"
    assert details["stderr_tail"] == "gate stderr"
