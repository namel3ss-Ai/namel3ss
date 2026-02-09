from __future__ import annotations

import json
from pathlib import Path

from tools.ui_baseline_refresh import (
    build_baseline_payloads,
    check_baselines,
    print_drift_report,
    write_baselines,
)


def test_ui_baseline_refresh_payloads_are_deterministic() -> None:
    first = build_baseline_payloads()
    second = build_baseline_payloads()
    assert first == second


def test_ui_baseline_refresh_write_is_byte_identical(tmp_path: Path) -> None:
    payloads = build_baseline_payloads()
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"

    first_written = write_baselines(payloads, root=first_root)
    second_written = write_baselines(payloads, root=second_root)

    assert first_written == second_written
    assert first_written
    for path in first_written:
        first_bytes = (first_root / path).read_bytes()
        second_bytes = (second_root / path).read_bytes()
        assert first_bytes == second_bytes


def test_ui_baseline_refresh_check_reports_fix_command(capsys, tmp_path: Path) -> None:
    path = Path("tests/fixtures/ui_manifest_baselines/test_case.json")
    payloads = {path: '{\n  "ok": true\n}\n'}
    target = tmp_path / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('{\n  "ok": false\n}\n', encoding="utf-8")

    drifted = check_baselines(payloads, root=tmp_path)
    assert drifted == [path]
    print_drift_report(drifted)

    captured = capsys.readouterr().out
    assert "Baseline drift detected:" in captured
    assert "tests/fixtures/ui_manifest_baselines/test_case.json" in captured
    assert "Run: python tools/ui_baseline_refresh.py --write" in captured


def test_tool_basic_snapshots_scrub_python_paths_and_trace_hashes() -> None:
    payloads = build_baseline_payloads()
    run_path = Path("tests/fixtures/golden_snapshots/tool_basic/run.json")
    traces_path = Path("tests/fixtures/golden_snapshots/tool_basic/traces.json")

    run_payload = payloads[run_path]
    traces_payload = payloads[traces_path]
    run_json = json.loads(run_payload)
    contract = run_json.get("contract") if isinstance(run_json, dict) else None

    assert "\"python_path\": \"<python>\"" in run_payload
    assert "\"python_path\": \"<python>\"" in traces_payload
    assert isinstance(contract, dict)
    assert isinstance(contract.get("trace_hash"), str)
    assert len(contract["trace_hash"]) == 64
