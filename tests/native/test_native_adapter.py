from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.runtime.native import NativeStatus, native_available, native_enabled, native_hash, native_info, native_scan, status_to_code
from namel3ss.runtime.native import adapter as native_adapter
from namel3ss.runtime.native import loader as native_loader
from namel3ss.runtime.native.status import status_values_are_unique

_ALLOWED_CODES = {
    "parse_error",
    "runtime_error",
    "tool_error",
    "provider_error",
    "capability_denied",
    "policy_denied",
    "internal_error",
}


@pytest.fixture(autouse=True)
def _reset_native_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("N3_NATIVE", raising=False)
    monkeypatch.delenv("N3_NATIVE_LIB", raising=False)
    native_loader._reset_native_state()


def test_native_disabled_by_default() -> None:
    assert native_enabled() is False
    assert native_available() is False
    outcome = native_info()
    assert outcome.status == NativeStatus.NOT_IMPLEMENTED
    assert outcome.payload is None
    assert outcome.error_code is None


def test_native_enabled_without_library_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("N3_NATIVE", "1")
    native_loader._reset_native_state()
    assert native_enabled() is True
    assert native_available() is False
    outcome = native_scan(b"flow \"demo\":\n  return 1\n")
    assert outcome.status == NativeStatus.NOT_IMPLEMENTED
    assert outcome.payload is None
    assert outcome.error_code is None


def test_native_missing_library_path_falls_back(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("N3_NATIVE", "1")
    missing = tmp_path / "missing-native-lib"
    monkeypatch.setenv("N3_NATIVE_LIB", str(missing))
    native_loader._reset_native_state()
    assert native_enabled() is True
    assert native_available() is False
    outcome = native_hash(b"hash")
    assert outcome.status == NativeStatus.NOT_IMPLEMENTED
    assert outcome.payload is None
    assert outcome.error_code is None


def test_status_mapping_is_stable() -> None:
    assert status_values_are_unique() is True
    assert status_to_code(NativeStatus.OK) is None
    assert status_to_code(NativeStatus.NOT_IMPLEMENTED) is None
    for status in (NativeStatus.INVALID_ARGUMENT, NativeStatus.INVALID_STATE, NativeStatus.ERROR):
        code = status_to_code(status)
        assert code in _ALLOWED_CODES


def test_fallback_policy_for_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("N3_NATIVE", "1")
    native_loader._reset_native_state()
    outcome = native_adapter.NativeOutcome(status=NativeStatus.ERROR, payload=b"x", error_code="internal_error")
    assert outcome.should_fallback() is True
