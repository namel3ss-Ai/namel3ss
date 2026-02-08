from __future__ import annotations

import json
import os
from pathlib import Path

from namel3ss.determinism import canonical_json_dumps
from tests.ui.ui_manifest_baseline_harness import (
    BASELINE_FIXTURES_DIR,
    UIBaselineCase,
    baseline_cases,
    build_case_snapshot,
)


def test_ui_manifest_baseline_goldens() -> None:
    update = os.getenv("UPDATE_UI_MANIFEST_BASELINES") == "1"
    BASELINE_FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    for case in baseline_cases():
        snapshot = build_case_snapshot(case)
        expected_path = _snapshot_path(case)
        if update:
            expected_path.write_text(canonical_json_dumps(snapshot, pretty=True), encoding="utf-8")
            continue
        assert expected_path.exists(), f"missing baseline snapshot: {expected_path}"
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        assert snapshot == expected


def test_ui_manifest_baselines_are_deterministic() -> None:
    for case in baseline_cases():
        first = build_case_snapshot(case)
        second = build_case_snapshot(case)
        assert first == second


def test_ui_manifest_baseline_expectations() -> None:
    for case in baseline_cases():
        snapshot = build_case_snapshot(case)
        summary = snapshot.get("summary", {}) if isinstance(snapshot, dict) else {}
        warning_codes = set(summary.get("warning_codes", []))
        element_types = set(summary.get("element_types", []))
        action_types = set(summary.get("action_types", []))
        expected_warning_codes = set(case.expected_warning_codes)

        if expected_warning_codes:
            assert expected_warning_codes.issubset(warning_codes)
        else:
            assert not warning_codes

        assert set(case.required_element_types).issubset(element_types)
        assert set(case.required_action_types).issubset(action_types)

        css_contract = snapshot.get("css_contract", {}) if isinstance(snapshot, dict) else {}
        assert css_contract.get("sticky_topbar") is True


def _snapshot_path(case: UIBaselineCase) -> Path:
    return BASELINE_FIXTURES_DIR / f"{case.name}.json"
