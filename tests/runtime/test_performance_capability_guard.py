from __future__ import annotations

import pytest

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.executor import execute_program_flow
from tests.conftest import lower_ir_program


SOURCE_WITHOUT_CAPABILITY = '''spec is "1.0"

flow "demo":
  return "ok"
'''


SOURCE_WITH_CAPABILITY = '''spec is "1.0"

capabilities:
  performance

flow "demo":
  return "ok"
'''


def _performance_config() -> AppConfig:
    config = AppConfig()
    config.performance.async_runtime = True
    config.performance.max_concurrency = 4
    config.performance.cache_size = 32
    config.performance.enable_batching = True
    return config


def test_performance_settings_require_capability() -> None:
    program = lower_ir_program(SOURCE_WITHOUT_CAPABILITY)
    with pytest.raises(Namel3ssError) as exc:
        execute_program_flow(program, "demo", config=_performance_config())
    assert "Performance runtime settings" in exc.value.message
    assert "performance" in exc.value.message


def test_performance_settings_allowed_with_capability() -> None:
    program = lower_ir_program(SOURCE_WITH_CAPABILITY)
    result = execute_program_flow(program, "demo", config=_performance_config())
    assert result.last_value == "ok"
