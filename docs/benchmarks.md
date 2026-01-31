# Benchmark

Deterministic benchmark runner for scan, lowering, audit rendering, ingestion gate throughput, and executor parity.

## Run

Deterministic report (default):

```sh
python tools/bench.py --out /tmp/namel3ss_bench.json
```

Optional real timing (non-gating, values will vary):

```sh
python tools/bench.py --timing real --out /tmp/namel3ss_bench.json
```

Attempt native executor timings when available:

```sh
python tools/bench.py --native-exec --out /tmp/namel3ss_bench.json
```

## Report

The report is canonical JSON with stable key ordering and no timestamps or paths. It includes:

- `report_signature`: hash of the runtime signature and suite/fixture definitions.
- `runtime_signature`: deterministic runtime contract signature.
- `timing_mode`: `deterministic` or `real`.
- `environment`: python version and platform tag.
- `suites`: per-suite cases with metrics and timing aggregates.

Timing fields are integer microseconds with fixed rounding rules; deterministic mode emits `total_us = 0`.

## CI

CI writes the report to:

```
.namel3ss/ci_artifacts/bench_report.json
```

Artifacts are informational only; they do not gate CI on performance numbers.
