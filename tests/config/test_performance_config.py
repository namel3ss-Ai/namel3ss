from __future__ import annotations

import pytest

from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError


def test_performance_defaults(tmp_path) -> None:
    cfg = load_config(root=tmp_path)
    assert cfg.performance.async_runtime is False
    assert cfg.performance.max_concurrency == 8
    assert cfg.performance.cache_size == 128
    assert cfg.performance.enable_batching is False
    assert cfg.performance.metrics_endpoint == "/api/metrics"


def test_performance_toml_values(tmp_path) -> None:
    path = tmp_path / "namel3ss.toml"
    path.write_text(
        (
            "[performance]\n"
            "async_runtime = true\n"
            "max_concurrency = 16\n"
            "cache_size = 64\n"
            "enable_batching = true\n"
            'metrics_endpoint = "/metrics/custom"\n'
        ),
        encoding="utf-8",
    )
    cfg = load_config(root=tmp_path)
    assert cfg.performance.async_runtime is True
    assert cfg.performance.max_concurrency == 16
    assert cfg.performance.cache_size == 64
    assert cfg.performance.enable_batching is True
    assert cfg.performance.metrics_endpoint == "/metrics/custom"


def test_performance_env_overrides(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("N3_ASYNC_RUNTIME", "true")
    monkeypatch.setenv("N3_MAX_CONCURRENCY", "12")
    monkeypatch.setenv("N3_CACHE_SIZE", "256")
    monkeypatch.setenv("N3_ENABLE_BATCHING", "yes")
    monkeypatch.setenv("N3_PERFORMANCE_METRICS_ENDPOINT", "/metrics/perf")
    cfg = load_config(root=tmp_path)
    assert cfg.performance.async_runtime is True
    assert cfg.performance.max_concurrency == 12
    assert cfg.performance.cache_size == 256
    assert cfg.performance.enable_batching is True
    assert cfg.performance.metrics_endpoint == "/metrics/perf"


def test_performance_invalid_max_concurrency_rejected(tmp_path) -> None:
    path = tmp_path / "namel3ss.toml"
    path.write_text("[performance]\nmax_concurrency = 0\n", encoding="utf-8")
    with pytest.raises(Namel3ssError) as exc:
        load_config(root=tmp_path)
    assert "performance.max_concurrency" in exc.value.message
