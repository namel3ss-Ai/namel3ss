from pathlib import Path

from namel3ss.release.model import GateSpec
from namel3ss.release.runner import (
    GateExecution,
    build_release_report,
    release_exit_code,
    write_release_report_json,
)


def _executor_ok(_gate, tests, _fast):
    return GateExecution(
        exit_code=0,
        duration_ms=5,
        command=("pytest", "-q", *tests),
        stdout="",
        stderr="",
    )


def _executor_fail(_gate, tests, _fast):
    return GateExecution(
        exit_code=1,
        duration_ms=7,
        command=("pytest", "-q", *tests),
        stdout="",
        stderr="",
    )


def test_release_report_deterministic(monkeypatch, tmp_path):
    root = Path(__file__).resolve().parents[2]
    monkeypatch.chdir(root)
    gates = (
        GateSpec(name="Gate A", tests=("tests/contract/test_contract_validate.py",), required=True),
        GateSpec(name="Gate B", tests=("tests/contract/test_contract_validate.py",), required=True),
    )
    report_a = build_release_report(gates=gates, executor=_executor_ok, fast=True)
    report_b = build_release_report(gates=gates, executor=_executor_ok, fast=True)
    assert report_a.as_dict() == report_b.as_dict()

    json_path_a = tmp_path / "report_a.json"
    json_path_b = tmp_path / "report_b.json"
    write_release_report_json(report_a, json_path_a)
    write_release_report_json(report_b, json_path_b)
    assert json_path_a.read_text(encoding="utf-8") == json_path_b.read_text(encoding="utf-8")


def test_release_report_missing_gate_fails(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    monkeypatch.chdir(root)
    gates = (GateSpec(name="Missing Gate", tests=("tests/does_not_exist.py",), required=True),)
    report = build_release_report(gates=gates, executor=_executor_ok)
    gate = report.gates[0]
    assert gate.status == "missing"
    assert gate.code == "missing_gate.missing"
    assert report.summary["missing"] == 1
    assert release_exit_code(report) == 1


def test_release_exit_code_nonzero_on_fail(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    monkeypatch.chdir(root)
    gates = (GateSpec(name="Failing Gate", tests=("tests/contract/test_contract_validate.py",), required=True),)
    report = build_release_report(gates=gates, executor=_executor_fail)
    assert report.gates[0].status == "fail"
    assert release_exit_code(report) == 1
