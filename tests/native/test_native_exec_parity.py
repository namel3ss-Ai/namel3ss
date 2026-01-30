from __future__ import annotations

import json
from pathlib import Path

import pytest

from namel3ss.determinism import canonical_json_dumps
from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse
from namel3ss.runtime.executor.api import execute_program_flow
from namel3ss.runtime.native.exec_adapter import _reset_exec_state, native_exec_available, native_exec_ir
from namel3ss.runtime.native.status import NativeStatus
from namel3ss.ir.serialize import dump_ir
from tests.spec_freeze.helpers.runtime_dump import dump_runtime

FIXTURES = Path("tests/fixtures/native_exec")


@pytest.fixture(autouse=True)
def _reset_exec(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("N3_NATIVE_EXEC", raising=False)
    monkeypatch.delenv("N3_NATIVE_LIB", raising=False)
    _reset_exec_state()


def test_native_exec_matches_python(monkeypatch: pytest.MonkeyPatch) -> None:
    source = (FIXTURES / "basic.ai").read_text(encoding="utf-8")
    expected = (FIXTURES / "basic.runtime.json").read_bytes()
    _assert_canonical_json(expected)

    program = lower_program(parse(source))
    python_result = execute_program_flow(
        program,
        "demo",
        state={},
        input=None,
        store=None,
        identity={"id": "user-1", "trust_level": "contributor"},
    )
    python_payload = canonical_json_dumps(dump_runtime(python_result), pretty=False).encode("utf-8")
    assert python_payload == expected

    monkeypatch.setenv("N3_NATIVE_EXEC", "1")
    _reset_exec_state()
    if not native_exec_available():
        pytest.skip("native executor not available")

    program_native = lower_program(parse(source))
    native_result = execute_program_flow(
        program_native,
        "demo",
        state={},
        input=None,
        store=None,
        identity={"id": "user-1", "trust_level": "contributor"},
    )
    native_payload = canonical_json_dumps(dump_runtime(native_result), pretty=False).encode("utf-8")
    assert native_payload == expected


def test_native_exec_unsupported_returns_not_implemented(monkeypatch: pytest.MonkeyPatch) -> None:
    source = (FIXTURES / "unsupported.ai").read_text(encoding="utf-8")
    program = lower_program(parse(source))
    ir_payload = dump_ir(program)
    ir_bytes = canonical_json_dumps(ir_payload, pretty=False).encode("utf-8")
    config = {
        "flow_name": "demo",
        "runtime_theme": getattr(program, "theme", None),
        "theme_source": "app",
    }
    config_bytes = canonical_json_dumps(config, pretty=False).encode("utf-8")

    monkeypatch.setenv("N3_NATIVE_EXEC", "1")
    _reset_exec_state()
    if not native_exec_available():
        pytest.skip("native executor not available")

    outcome = native_exec_ir(ir_bytes, config_bytes)
    assert outcome.status == NativeStatus.NOT_IMPLEMENTED


def test_native_exec_falls_back_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    source = (FIXTURES / "basic.ai").read_text(encoding="utf-8")
    expected = (FIXTURES / "basic.runtime.json").read_bytes()
    monkeypatch.setenv("N3_NATIVE_EXEC", "1")
    monkeypatch.setenv("N3_NATIVE_LIB", "/missing/native/library")
    _reset_exec_state()

    program = lower_program(parse(source))
    result = execute_program_flow(
        program,
        "demo",
        state={},
        input=None,
        store=None,
        identity={"id": "user-1", "trust_level": "contributor"},
    )
    payload = canonical_json_dumps(dump_runtime(result), pretty=False).encode("utf-8")
    assert payload == expected


def _assert_canonical_json(payload: bytes) -> None:
    data = json.loads(payload.decode("utf-8"))
    canonical = canonical_json_dumps(data, pretty=False).encode("utf-8")
    assert canonical == payload
