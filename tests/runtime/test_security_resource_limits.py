from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse
from namel3ss.runtime.executor.api import execute_program_flow
from namel3ss.runtime.store.memory_store import MemoryStore


SOURCE_WITH_SECURITY_CAPABILITY = '''spec is "1.0"

capabilities:
  security_compliance

flow "demo":
  return input.payload
'''

SOURCE_WITHOUT_SECURITY_CAPABILITY = '''spec is "1.0"

flow "demo":
  return input.payload
'''


def _build_program(tmp_path: Path, source: str):
    app_path = tmp_path / "app.ai"
    app_path.write_text(source, encoding="utf-8")
    program = lower_program(parse(source))
    program.project_root = tmp_path.as_posix()
    program.app_path = app_path.as_posix()
    return program


def _write_security_yaml(tmp_path: Path, *, max_memory_mb: int, max_cpu_ms: int) -> None:
    (tmp_path / "security.yaml").write_text(
        (
            'version: "1.0"\n'
            "encryption:\n"
            "  enabled: true\n"
            '  algorithm: "aes-256-gcm"\n'
            "  key: env:N3_ENCRYPTION_KEY\n"
            "resource_limits:\n"
            f"  max_memory_mb: {int(max_memory_mb)}\n"
            f"  max_cpu_ms: {int(max_cpu_ms)}\n"
        ),
        encoding="utf-8",
    )


def test_cpu_step_limit_blocks_execution_when_security_capability_enabled(tmp_path: Path) -> None:
    program = _build_program(tmp_path, SOURCE_WITH_SECURITY_CAPABILITY)
    _write_security_yaml(tmp_path, max_memory_mb=64, max_cpu_ms=1)

    with pytest.raises(Namel3ssError) as exc:
        execute_program_flow(
            program,
            "demo",
            input={"payload": "ok"},
            store=MemoryStore(),
        )
    assert "CPU logical step limit exceeded" in exc.value.message


def test_memory_limit_blocks_execution_when_security_capability_enabled(tmp_path: Path) -> None:
    program = _build_program(tmp_path, SOURCE_WITH_SECURITY_CAPABILITY)
    _write_security_yaml(tmp_path, max_memory_mb=1, max_cpu_ms=5000)

    payload = {"payload": "x" * (2 * 1024 * 1024)}
    with pytest.raises(Namel3ssError) as exc:
        execute_program_flow(
            program,
            "demo",
            input=payload,
            store=MemoryStore(),
        )
    assert "Memory limit exceeded" in exc.value.message


def test_limits_are_not_applied_without_security_capability(tmp_path: Path) -> None:
    program = _build_program(tmp_path, SOURCE_WITHOUT_SECURITY_CAPABILITY)
    _write_security_yaml(tmp_path, max_memory_mb=1, max_cpu_ms=1)

    result = execute_program_flow(
        program,
        "demo",
        input={"payload": "ok"},
        store=MemoryStore(),
    )
    assert result.last_value == "ok"
