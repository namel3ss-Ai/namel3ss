from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

from namel3ss.cli.doc_mode import build_doc_payload
from namel3ss.determinism import canonical_json_dumps
from namel3ss.ingestion.detect import detect_upload
from namel3ss.ingestion.gate import gate_quality
from namel3ss.ingestion.gate_cache import gate_root, read_cache_entry
from namel3ss.ingestion.gate_probe import probe_content
from namel3ss.ingestion.normalize import normalize_text
from namel3ss.ingestion.quality_gate import evaluate_gate
from namel3ss.ingestion.signals import compute_signals
from namel3ss.ir.nodes import lower_program
from namel3ss.ir.serialize import dump_ir
from namel3ss.lexer.lexer import Lexer
from namel3ss.lexer.scan_payload import tokens_to_payload
from namel3ss.parser.core import parse
from namel3ss.runtime.audit import audit_report_json, build_audit_report, build_decision_model
from namel3ss.runtime.executor.api import execute_program_flow
from namel3ss.runtime.native.exec_adapter import _reset_exec_state, native_exec_available
from namel3ss.spec_freeze.v1.rules import NONDETERMINISTIC_KEYS, NORMALIZED_VALUE, PATH_KEYS

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_SUBSTRINGS = ("/Users/", "/home/", "C:\\")


@dataclass(frozen=True)
class BenchConfig:
    iterations: int
    timing_mode: str
    native_exec: bool


@dataclass(frozen=True)
class BenchTiming:
    total_us: int

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deterministic benchmark runner.")
    parser.add_argument("--out", help="Write report JSON to path (default: stdout).")
    parser.add_argument("--iterations", type=int, default=3, help="Iterations per case.")
    parser.add_argument(
        "--timing",
        choices=("deterministic", "real"),
        default="deterministic",
        help="Timing mode: deterministic (default) or real.",
    )
    parser.add_argument(
        "--native-exec",
        action="store_true",
        help="Enable native executor timing when available.",
    )
    args = parser.parse_args(argv)
    config = BenchConfig(iterations=max(1, int(args.iterations)), timing_mode=args.timing, native_exec=args.native_exec)
    report = build_report(config)
    text = canonical_json_dumps(report, pretty=True, drop_run_keys=False)
    _assert_no_forbidden(text)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0

def build_report(config: BenchConfig) -> dict:
    runtime_signature = build_doc_payload().get("runtime_signature", "")
    suites = []
    suites.append(_bench_scan(config))
    suites.append(_bench_lowering(config))
    suites.append(_bench_audit(config))
    suites.append(_bench_ingestion_gate(config))
    suites.append(_bench_exec_parity(config))
    fixture_sets = _fixture_sets()
    suite_defs = _suite_definitions(suites)
    report_signature = _report_signature(runtime_signature, suite_defs, fixture_sets)
    return {
        "report_signature": report_signature,
        "runtime_signature": runtime_signature,
        "timing_mode": config.timing_mode,
        "environment": _environment_payload(),
        "suites": suites,
    }

def _bench_scan(config: BenchConfig) -> dict:
    source = _read_text_fixture("native", "scan_basic.ai")
    source_bytes = source.encode("utf-8")
    token_count = 0
    payload_bytes = 0
    def _run() -> None:
        nonlocal token_count, payload_bytes
        tokens = Lexer(source)._tokenize_python()
        payload = tokens_to_payload(tokens)
        token_count = len(tokens)
        payload_bytes = len(payload)

    timing = _measure(config, _run)
    metrics = {
        "bytes_in": len(source_bytes),
        "tokens": token_count,
        "payload_bytes": payload_bytes,
    }
    return _suite_entry("scan", [_case_entry("scan_basic", config.iterations, metrics, timing)])

def _bench_lowering(config: BenchConfig) -> dict:
    source = _read_text_fixture("templates", "starter_template.ai")
    ir_bytes = 0
    node_count = 0
    def _run() -> None:
        nonlocal ir_bytes, node_count
        program = lower_program(parse(_ensure_spec(source)))
        payload = dump_ir(program)
        data = canonical_json_dumps(payload, pretty=False, drop_run_keys=False).encode("utf-8")
        ir_bytes = len(data)
        node_count = _count_ir_nodes(payload)

    timing = _measure(config, _run)
    metrics = {
        "source_bytes": len(source.encode("utf-8")),
        "ir_nodes": node_count,
        "ir_bytes": ir_bytes,
    }
    return _suite_entry("lowering", [_case_entry("starter_template", config.iterations, metrics, timing)])

def _bench_audit(config: BenchConfig) -> dict:
    payload = json.loads(_read_text_fixture("doctor", "audit_input.json"))
    state = payload.get("state") if isinstance(payload, dict) else {}
    traces = payload.get("traces") if isinstance(payload, dict) else []
    output_bytes = 0
    decision_count = 0
    def _run() -> None:
        nonlocal output_bytes, decision_count
        model = build_decision_model(
            state=state if isinstance(state, dict) else {},
            traces=traces if isinstance(traces, list) else [],
            project_root=None,
            app_path=None,
            policy_decl=None,
            identity=None,
            upload_id=None,
            query=None,
            secret_values=[],
        )
        report = build_audit_report(model, project_root=None, app_path=None, secret_values=[])
        decision_count = len(report.get("decisions", [])) if isinstance(report, dict) else 0
        output_bytes = len(audit_report_json(report, pretty=False).encode("utf-8"))

    timing = _measure(config, _run)
    metrics = {
        "output_bytes": output_bytes,
        "decisions": decision_count,
    }
    return _suite_entry("audit_render", [_case_entry("audit_basic", config.iterations, metrics, timing)])

def _bench_ingestion_gate(config: BenchConfig) -> dict:
    cases = []
    with tempfile.TemporaryDirectory(prefix="namel3ss-bench-ingest-") as temp_root:
        with _env_override({"N3_PERSIST_ROOT": temp_root}):
            for name, filename, content_type in _ingestion_fixture_defs():
                content = _read_bytes_fixture("ingestion_gate", filename)
                metrics, timing = _run_ingestion_case(
                    name=name,
                    content=content,
                    content_type=content_type,
                    iterations=config.iterations,
                    timing_mode=config.timing_mode,
                )
                cases.append(_case_entry(name, config.iterations, metrics, timing))
    return _suite_entry("ingestion_gate", cases)

def _bench_exec_parity(config: BenchConfig) -> dict:
    source = _read_text_fixture("native_exec", "basic.ai")
    expected = _read_bytes_fixture("native_exec", "basic.runtime.json")
    python_bytes = 0
    native_bytes = 0
    native_available = False
    parity_ok = False
    def _run_python() -> None:
        nonlocal python_bytes, parity_ok
        result = _execute_flow(source)
        payload = canonical_json_dumps(_dump_runtime(result), pretty=False, drop_run_keys=False).encode("utf-8")
        python_bytes = len(payload)
        if payload != expected:
            raise RuntimeError("python executor output drifted from golden.")
        parity_ok = True
    def _run_native() -> None:
        nonlocal native_bytes, native_available, parity_ok
        with _env_override({"N3_NATIVE_EXEC": "1"}):
            _reset_exec_state()
            if not native_exec_available():
                native_available = False
                return
            native_available = True
            result = _execute_flow(source)
            payload = canonical_json_dumps(_dump_runtime(result), pretty=False, drop_run_keys=False).encode("utf-8")
            native_bytes = len(payload)
            if payload != expected:
                raise RuntimeError("native executor output drifted from golden.")
            parity_ok = True

    python_timing = _measure(config, _run_python)
    native_timing = BenchTiming(total_us=0)
    if config.native_exec:
        native_timing = _measure(config, _run_native)

    metrics = {
        "python_output_bytes": python_bytes,
        "native_output_bytes": native_bytes if native_available else None,
        "native_available": native_available,
        "parity_ok": parity_ok,
    }
    timings = {
        "python": _timing_payload(python_timing, python_bytes),
        "native": _timing_payload(native_timing, native_bytes) if native_available else None,
    }
    return _suite_entry("exec_parity", [_case_entry("native_exec_basic", config.iterations, metrics, timings)])

def _run_ingestion_case(
    *,
    name: str,
    content: bytes,
    content_type: str,
    iterations: int,
    timing_mode: str,
) -> tuple[dict, BenchTiming]:
    metadata = {"content_type": content_type, "name": name}
    detected = detect_upload(metadata, content=content)
    probe = probe_content(content, metadata=metadata, detected=detected)
    normalized_text = None
    if probe.get("status") != "block":
        normalized_text = normalize_text(_decode_text(content))
    signals = compute_signals(normalized_text or "", detected=detected)
    quality_status, quality_reasons = gate_quality(signals)
    cache_hits = 0
    cache_misses = 0
    last_status = None
    last_bytes = len(content)
    cache_key = None
    def _run_once() -> None:
        nonlocal cache_hits, cache_misses, last_status, cache_key
        root = gate_root(None, None)
        cached_before = False
        if root is not None and cache_key is not None:
            cached_before = read_cache_entry(root, cache_key) is not None
        decision = evaluate_gate(
            content=content,
            metadata=metadata,
            detected=detected,
            normalized_text=normalized_text,
            quality_status=quality_status,
            quality_reasons=quality_reasons,
            project_root=None,
            app_path=None,
            secret_values=[],
            probe=probe,
            enable_chunk_plan=False,
        )
        cache_key = None
        if isinstance(decision, dict):
            last_status = decision.get("status")
            cache = decision.get("cache")
            if isinstance(cache, dict):
                cache_key = cache.get("key")
        if cached_before:
            cache_hits += 1
        else:
            cache_misses += 1

    timing = _measure(BenchConfig(iterations=iterations, timing_mode=timing_mode, native_exec=False), _run_once)
    metrics = {
        "bytes_in": last_bytes,
        "status": last_status,
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
    }
    return metrics, timing

def _execute_flow(source: str):
    program = lower_program(parse(_ensure_spec(source)))
    return execute_program_flow(
        program,
        "demo",
        state={},
        input=None,
        store=None,
        identity={"id": "user-1", "trust_level": "contributor"},
    )

def _dump_runtime(result: Any) -> dict:
    return {
        "state": _to_data(getattr(result, "state", None), key_name="state"),
        "last_value": _to_data(getattr(result, "last_value", None), key_name="last_value"),
        "execution_steps": _to_data(getattr(result, "execution_steps", None), key_name="execution_steps"),
        "traces": _to_data(getattr(result, "traces", None), key_name="traces"),
        "runtime_theme": _to_data(getattr(result, "runtime_theme", None), key_name="runtime_theme"),
        "theme_source": _to_data(getattr(result, "theme_source", None), key_name="theme_source"),
    }

def _to_data(value: Any, *, key_name: str | None = None) -> Any:
    if key_name in NONDETERMINISTIC_KEYS:
        return NORMALIZED_VALUE
    if key_name in PATH_KEYS:
        return _normalize_path(value)
    if _is_dataclass(value):
        data = {"type": value.__class__.__name__}
        for field in value.__dataclass_fields__.values():
            data[field.name] = _to_data(getattr(value, field.name), key_name=field.name)
        return data
    if isinstance(value, dict):
        return {key: _to_data(value[key], key_name=str(key)) for key in sorted(value.keys(), key=str)}
    if isinstance(value, list):
        return [_to_data(item) for item in value]
    if isinstance(value, tuple):
        return [_to_data(item) for item in value]
    if isinstance(value, set):
        return sorted((_to_data(item) for item in value), key=str)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Path):
        return _normalize_path(value)
    return value

def _normalize_path(value: Any) -> Any:
    if isinstance(value, Path):
        return NORMALIZED_VALUE if value.is_absolute() else str(value)
    if isinstance(value, str):
        return NORMALIZED_VALUE if Path(value).is_absolute() else value
    return value

def _is_dataclass(value: Any) -> bool:
    return hasattr(value, "__dataclass_fields__")

def _measure(config: BenchConfig, fn: Callable[[], None]) -> BenchTiming:
    if config.timing_mode != "real":
        for _ in range(config.iterations):
            fn()
        return BenchTiming(total_us=0)
    start = time.perf_counter_ns()
    for _ in range(config.iterations):
        fn()
    elapsed_ns = time.perf_counter_ns() - start
    return BenchTiming(total_us=max(0, int(elapsed_ns // 1000)))

def _timing_payload(timing: BenchTiming, units: int) -> dict:
    throughput = None
    if timing.total_us > 0 and units >= 0:
        throughput = int((units * 1_000_000) // max(1, timing.total_us))
    return {"total_us": timing.total_us, "throughput_units_per_s": throughput}

def _suite_entry(name: str, cases: list[dict]) -> dict:
    return {"name": name, "cases": cases}

def _case_entry(name: str, iterations: int, metrics: dict, timing: BenchTiming | dict) -> dict:
    payload = {
        "name": name,
        "iterations": iterations,
        "metrics": metrics,
    }
    if isinstance(timing, BenchTiming):
        payload["timing"] = _timing_payload(timing, _units_from_metrics(metrics))
    else:
        payload["timing"] = timing
    return payload

def _units_from_metrics(metrics: dict) -> int:
    for key in ("bytes_in", "output_bytes", "ir_bytes"):
        value = metrics.get(key)
        if isinstance(value, int):
            return value
    return 0

def _environment_payload() -> dict:
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    platform = "windows" if os.name == "nt" else "posix"
    return {"python": version, "platform": platform}

def _fixture_sets() -> dict:
    return {
        "scan_basic": "scan_basic",
        "starter_template": "starter_template",
        "audit_basic": "audit_basic",
        "ingestion_valid": "ingestion_valid",
        "ingestion_cracked_null": "ingestion_cracked_null",
        "ingestion_redact": "ingestion_redact",
        "native_exec_basic": "native_exec_basic",
    }

def _suite_definitions(suites: list[dict]) -> list[dict]:
    definitions = []
    for suite in suites:
        name = suite.get("name")
        cases = suite.get("cases") if isinstance(suite, dict) else []
        case_names = []
        if isinstance(cases, list):
            for case in cases:
                if isinstance(case, dict) and case.get("name"):
                    case_names.append(str(case.get("name")))
        definitions.append({"name": name, "cases": case_names})
    return definitions

def _report_signature(runtime_signature: str, suite_defs: list[dict], fixture_sets: dict) -> str:
    payload = {
        "runtime_signature": runtime_signature,
        "suite_definitions": suite_defs,
        "fixture_sets": fixture_sets,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

def _ensure_spec(code: str) -> str:
    for line in code.splitlines():
        if line.strip().startswith('spec is "'):
            return code
    return 'spec is "1.0"\n\n' + code.lstrip("\n")

def _count_ir_nodes(value: object) -> int:
    if isinstance(value, dict):
        count = 1 if "type" in value else 0
        for item in value.values():
            count += _count_ir_nodes(item)
        return count
    if isinstance(value, list):
        return sum(_count_ir_nodes(item) for item in value)
    return 0

def _read_text_fixture(*parts: str) -> str:
    return (ROOT / "tests" / "fixtures" / Path(*parts)).read_text(encoding="utf-8")

def _read_bytes_fixture(*parts: str) -> bytes:
    return (ROOT / "tests" / "fixtures" / Path(*parts)).read_bytes()

def _ingestion_fixture_defs() -> list[tuple[str, str, str]]:
    return [
        ("valid", "valid.txt", "text/plain"),
        ("cracked_null", "cracked_null.bin", "application/octet-stream"),
        ("redact", "redact.txt", "text/plain"),
    ]

def _decode_text(payload: bytes) -> str:
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError:
        return payload.decode("latin-1")

def _assert_no_forbidden(text: str) -> None:
    for marker in FORBIDDEN_SUBSTRINGS:
        if marker in text:
            raise RuntimeError("bench output contains forbidden host path markers")

class _EnvOverride:
    def __init__(self, updates: dict[str, str]) -> None:
        self._updates = updates
        self._original: dict[str, str | None] = {}
    def __enter__(self) -> "_EnvOverride":
        for key, value in self._updates.items():
            self._original[key] = os.getenv(key)
            os.environ[key] = value
        return self
    def __exit__(self, exc_type, exc, tb) -> None:
        for key, value in self._original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

def _env_override(updates: dict[str, str]) -> _EnvOverride:
    return _EnvOverride(updates)


__all__ = ["BenchConfig", "build_report", "main"]
if __name__ == "__main__":
    raise SystemExit(main())
