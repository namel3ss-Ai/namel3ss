from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.cli import run_mode


def test_parse_run_performance_flags() -> None:
    params = run_mode._parse_args(
        [
            "--async-runtime",
            "true",
            "--max-concurrency",
            "12",
            "--cache-size",
            "256",
            "--enable-batching",
            "false",
        ]
    )
    assert params.async_runtime is True
    assert params.max_concurrency == 12
    assert params.cache_size == 256
    assert params.enable_batching is False


def test_parse_run_performance_flags_reject_invalid_bool() -> None:
    with pytest.raises(Namel3ssError) as exc:
        run_mode._parse_args(["--async-runtime", "maybe"])
    assert "--async-runtime must be true or false" in exc.value.message


def test_parse_run_performance_flags_reject_invalid_concurrency() -> None:
    with pytest.raises(Namel3ssError) as exc:
        run_mode._parse_args(["--max-concurrency", "0"])
    assert "--max-concurrency must be >= 1" in exc.value.message
