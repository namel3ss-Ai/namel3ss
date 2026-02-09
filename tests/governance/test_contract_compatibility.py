from __future__ import annotations

from pathlib import Path

from namel3ss.runtime.contracts.runtime_schema import runtime_contract_schema_catalog
from tools.contract_compat_check import BASELINE_PATH, check_contract_compatibility, load_catalog


def test_runtime_contract_baseline_exists() -> None:
    assert BASELINE_PATH.exists()
    payload = load_catalog(BASELINE_PATH)
    assert isinstance(payload, dict)
    assert payload.get("schemas")


def test_runtime_contracts_are_backward_compatible_with_baseline() -> None:
    baseline = load_catalog(BASELINE_PATH)
    current = runtime_contract_schema_catalog()
    issues = check_contract_compatibility(baseline, current)
    assert issues == []


def test_runtime_contract_baseline_has_expected_file_path() -> None:
    expected = Path("resources/runtime_contract_schema_v1.json")
    assert BASELINE_PATH == expected
