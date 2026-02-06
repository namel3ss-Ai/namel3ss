#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
import time
import tracemalloc
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from namel3ss.compilation.runner import clean_compiled_artifacts, compile_flow_to_target
from namel3ss.determinism import canonical_json_dumps
from namel3ss.module_loader import load_project
from namel3ss.runtime.run_pipeline import build_flow_payload

DEFAULT_SAMPLE_APP = ROOT / "scripts" / "fixtures" / "baseline_sample.ai"
DEFAULT_OUTPUT = ROOT / "docs" / "reports" / "baseline_metrics.json"
DEFAULT_WORKSPACE = ROOT / ".namel3ss" / "baseline_metrics_workspace"


class MetricsFailure(RuntimeError):
    """Raised when baseline metrics cannot be collected."""


@dataclass(frozen=True)
class MetricsConfig:
    repo_root: Path
    sample_app: Path
    output: Path
    iterations: int
    timing_mode: str


@dataclass(frozen=True)
class IterationSample:
    duration_ms: float
    payload_bytes: int


def collect_baseline_metrics(config: MetricsConfig) -> dict[str, object]:
    sample_source = _read_sample_source(config.sample_app)
    _require_valid_mode(config.timing_mode)

    workspace = DEFAULT_WORKSPACE
    app_path = workspace / "app.ai"
    out_dir = workspace / "compiled"

    compile_samples: list[IterationSample] = []
    runtime_samples: list[IterationSample] = []

    tracemalloc.start()
    try:
        _reset_workspace(workspace)
        app_path.parent.mkdir(parents=True, exist_ok=True)
        app_path.write_text(sample_source, encoding="utf-8")

        compile_samples = _collect_compile_samples(
            app_path=app_path,
            out_dir=out_dir,
            source_text=sample_source,
            iterations=config.iterations,
            timing_mode=config.timing_mode,
        )

        runtime_samples = _collect_runtime_samples(
            app_path=app_path,
            iterations=config.iterations,
            timing_mode=config.timing_mode,
        )

        current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
        _safe_cleanup(workspace)

    if not compile_samples:
        raise MetricsFailure("Compile benchmark produced no samples.")
    if not runtime_samples:
        raise MetricsFailure("Runtime benchmark produced no samples.")

    compile_time_ms = _average(sample.duration_ms for sample in compile_samples)
    runtime_latency_ms = _average(sample.duration_ms for sample in runtime_samples)

    source_bytes = len(sample_source.encode("utf-8"))
    generated_bytes = compile_samples[-1].payload_bytes
    runtime_bytes = runtime_samples[-1].payload_bytes

    if config.timing_mode == "deterministic":
        memory_usage_kb = round((source_bytes + generated_bytes + runtime_bytes) / 8.0, 3)
        measured_at = "1970-01-01T00:00:00Z"
    else:
        _ = current
        memory_usage_kb = round(peak / 1024.0, 3)
        measured_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    payload = {
        "schema_version": 1,
        "timing_mode": config.timing_mode,
        "sample_program": "scripts/fixtures/baseline_sample.ai",
        "compile_target": "python",
        "flow_name": "add",
        "iterations": config.iterations,
        "compile_time_ms": round(compile_time_ms, 3),
        "average_runtime_latency_ms": round(runtime_latency_ms, 3),
        "memory_usage_kb": memory_usage_kb,
        "measured_at": measured_at,
        "compile_runs_ms": [round(sample.duration_ms, 3) for sample in compile_samples],
        "runtime_runs_ms": [round(sample.duration_ms, 3) for sample in runtime_samples],
    }
    _validate_metrics_payload(payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure deterministic baseline compile/runtime metrics.")
    parser.add_argument("--repo-root", default=str(ROOT), help="Repository root path.")
    parser.add_argument("--sample-app", default=str(DEFAULT_SAMPLE_APP), help="Sample .ai program for measurement.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="JSON output path.")
    parser.add_argument("--iterations", type=int, default=5, help="Sequential iterations per benchmark.")
    parser.add_argument(
        "--timing",
        choices=("deterministic", "real"),
        default="deterministic",
        help="Timing mode. deterministic is CI-safe; real is non-gating and host-dependent.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate that generated metrics match --output without writing.",
    )
    args = parser.parse_args(argv)

    config = MetricsConfig(
        repo_root=Path(args.repo_root).resolve(),
        sample_app=Path(args.sample_app).resolve(),
        output=Path(args.output).resolve(),
        iterations=max(1, int(args.iterations)),
        timing_mode=str(args.timing),
    )

    if args.check and config.timing_mode != "deterministic":
        print("Metrics check mode only supports --timing deterministic.", file=sys.stderr)
        return 1

    try:
        payload = collect_baseline_metrics(config)
    except MetricsFailure as err:
        print(f"Metrics collection failed: {err}", file=sys.stderr)
        return 1

    text = canonical_json_dumps(payload, pretty=True, drop_run_keys=False)

    if args.check:
        if not config.output.exists():
            print(f"Metrics check failed: missing report file: {config.output}", file=sys.stderr)
            return 1
        existing = config.output.read_text(encoding="utf-8")
        if existing != text:
            print(
                "Metrics check failed: generated report differs from committed output. "
                "Re-run scripts/measure_baseline.py and commit the result.",
                file=sys.stderr,
            )
            return 1
        print(f"Metrics check passed: {config.output}")
        return 0

    config.output.parent.mkdir(parents=True, exist_ok=True)
    config.output.write_text(text, encoding="utf-8")
    print(f"Baseline metrics written: {config.output}")
    return 0


def _collect_compile_samples(
    *,
    app_path: Path,
    out_dir: Path,
    source_text: str,
    iterations: int,
    timing_mode: str,
) -> list[IterationSample]:
    samples: list[IterationSample] = []
    source_lines = len(source_text.splitlines())

    for index in range(iterations):
        _ = index
        clean_compiled_artifacts(app_path=app_path, out_dir=out_dir)

        start_ns = time.perf_counter_ns()
        try:
            payload = compile_flow_to_target(
                app_path=app_path,
                language="python",
                flow_name="add",
                out_dir=out_dir,
                build=False,
            )
        except Exception as err:
            raise MetricsFailure(f"compile benchmark failed: {err}") from err
        end_ns = time.perf_counter_ns()

        generated_bytes = _sum_generated_bytes(payload)
        if timing_mode == "real":
            duration_ms = (end_ns - start_ns) / 1_000_000.0
        else:
            duration_ms = _deterministic_compile_ms(source_lines=source_lines, generated_bytes=generated_bytes)

        samples.append(IterationSample(duration_ms=duration_ms, payload_bytes=generated_bytes))
    return samples


def _collect_runtime_samples(
    *,
    app_path: Path,
    iterations: int,
    timing_mode: str,
) -> list[IterationSample]:
    try:
        project = load_project(app_path)
    except Exception as err:
        raise MetricsFailure(f"could not load sample app: {err}") from err

    runtime_input = {"a": 2, "b": 3}
    input_bytes = len(canonical_json_dumps(runtime_input, pretty=False, drop_run_keys=False).encode("utf-8"))

    samples: list[IterationSample] = []
    for index in range(iterations):
        _ = index
        start_ns = time.perf_counter_ns()
        try:
            outcome = build_flow_payload(project.program, "add", input=runtime_input)
        except Exception as err:
            raise MetricsFailure(f"runtime benchmark failed: {err}") from err
        end_ns = time.perf_counter_ns()

        payload_json = canonical_json_dumps(outcome.payload, pretty=False, drop_run_keys=False)
        payload_bytes = len(payload_json.encode("utf-8"))
        if not bool(outcome.payload.get("ok")):
            raise MetricsFailure("runtime benchmark returned a non-ok payload.")

        if timing_mode == "real":
            duration_ms = (end_ns - start_ns) / 1_000_000.0
        else:
            duration_ms = _deterministic_runtime_ms(payload_bytes=payload_bytes, input_bytes=input_bytes)

        samples.append(IterationSample(duration_ms=duration_ms, payload_bytes=payload_bytes))
    return samples


def _sum_generated_bytes(payload: dict[str, object]) -> int:
    files = payload.get("files")
    if not isinstance(files, list):
        raise MetricsFailure("compile payload does not contain a valid files list.")

    total = 0
    for item in files:
        file_path = Path(str(item))
        if not file_path.exists() or not file_path.is_file():
            raise MetricsFailure(f"compile output file is missing: {file_path}")
        total += file_path.stat().st_size
    return total


def _validate_metrics_payload(payload: dict[str, object]) -> None:
    required_keys = {
        "compile_time_ms",
        "average_runtime_latency_ms",
        "memory_usage_kb",
        "measured_at",
    }
    missing = sorted(required_keys - set(payload.keys()))
    if missing:
        raise MetricsFailure(f"metrics payload missing required keys: {', '.join(missing)}")


def _deterministic_compile_ms(*, source_lines: int, generated_bytes: int) -> float:
    return round(1.0 + (source_lines * 0.12) + (generated_bytes / 2048.0), 3)


def _deterministic_runtime_ms(*, payload_bytes: int, input_bytes: int) -> float:
    return round(0.5 + (payload_bytes / 4096.0) + (input_bytes / 512.0), 3)


def _average(values) -> float:
    items = list(values)
    if not items:
        return 0.0
    return float(sum(items) / len(items))


def _read_sample_source(sample_app: Path) -> str:
    if not sample_app.exists():
        raise MetricsFailure(f"Missing sample app: {sample_app}")
    if not sample_app.is_file():
        raise MetricsFailure(f"Sample app path is not a file: {sample_app}")
    try:
        source = sample_app.read_text(encoding="utf-8")
    except OSError as err:
        raise MetricsFailure(f"Could not read sample app: {sample_app} ({err})") from err
    if not source.strip():
        raise MetricsFailure(f"Sample app is empty: {sample_app}")
    return source


def _reset_workspace(workspace: Path) -> None:
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True, exist_ok=True)


def _safe_cleanup(workspace: Path) -> None:
    try:
        if workspace.exists():
            shutil.rmtree(workspace)
    except OSError:
        return


def _require_valid_mode(mode: str) -> None:
    if mode not in {"deterministic", "real"}:
        raise MetricsFailure(f"Unsupported timing mode: {mode}")


if __name__ == "__main__":
    raise SystemExit(main())
