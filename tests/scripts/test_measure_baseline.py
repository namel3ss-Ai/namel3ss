from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    module_path = Path("scripts/measure_baseline.py").resolve()
    spec = importlib.util.spec_from_file_location("measure_baseline", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _default_config(module, tmp_path: Path, *, iterations: int = 2, timing_mode: str = "deterministic"):
    return module.MetricsConfig(
        repo_root=Path.cwd(),
        sample_app=Path("scripts/fixtures/baseline_sample.ai").resolve(),
        output=tmp_path / "baseline_metrics.json",
        iterations=iterations,
        timing_mode=timing_mode,
    )


def test_collect_baseline_metrics_is_deterministic(tmp_path: Path) -> None:
    module = _load_module()
    config = _default_config(module, tmp_path, iterations=2, timing_mode="deterministic")

    first = module.collect_baseline_metrics(config)
    second = module.collect_baseline_metrics(config)
    assert first == second

    assert first["compile_time_ms"] > 0
    assert first["average_runtime_latency_ms"] > 0
    assert first["memory_usage_kb"] > 0
    assert first["measured_at"] == "1970-01-01T00:00:00Z"
    assert set(first.keys()) >= {
        "compile_time_ms",
        "average_runtime_latency_ms",
        "memory_usage_kb",
        "measured_at",
    }


def test_real_timing_mode_can_be_controlled_with_mocked_clock(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    config = _default_config(module, tmp_path, iterations=1, timing_mode="real")

    ticks = iter([0, 2_000_000, 3_000_000, 4_500_000])
    monkeypatch.setattr(module.time, "perf_counter_ns", lambda: next(ticks))

    payload = module.collect_baseline_metrics(config)
    assert payload["compile_time_ms"] == 2.0
    assert payload["average_runtime_latency_ms"] == 1.5
    assert str(payload["measured_at"]).endswith("Z")


def test_main_write_and_check_mode(tmp_path: Path) -> None:
    module = _load_module()
    out_path = tmp_path / "baseline_metrics.json"

    rc = module.main(["--output", str(out_path), "--timing", "deterministic", "--iterations", "1"])
    assert rc == 0
    assert out_path.exists()

    rc = module.main(
        [
            "--output",
            str(out_path),
            "--timing",
            "deterministic",
            "--iterations",
            "1",
            "--check",
        ]
    )
    assert rc == 0

    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert set(data.keys()) >= {
        "compile_time_ms",
        "average_runtime_latency_ms",
        "memory_usage_kb",
        "measured_at",
    }

    out_path.write_text("{}\n", encoding="utf-8")
    rc = module.main(
        [
            "--output",
            str(out_path),
            "--timing",
            "deterministic",
            "--iterations",
            "1",
            "--check",
        ]
    )
    assert rc == 1


def test_main_fails_for_missing_sample_app(tmp_path: Path) -> None:
    module = _load_module()
    missing = tmp_path / "missing_sample.ai"
    out_path = tmp_path / "baseline_metrics.json"

    rc = module.main(["--sample-app", str(missing), "--output", str(out_path)])
    assert rc == 1
