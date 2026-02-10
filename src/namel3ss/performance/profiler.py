from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
import tracemalloc
from typing import Callable, Iterable, Mapping

from namel3ss.cli.app_loader import load_program
from namel3ss.config.loader import load_config
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.validation_entrypoint import build_static_manifest

_STAGE_ORDER: tuple[str, ...] = (
    "load_program",
    "build_manifest",
    "serialize_manifest",
)


@dataclass(frozen=True)
class StageMetric:
    stage: str
    elapsed_ms: float
    peak_memory_kb: int
    iterations: int

    def as_dict(self) -> dict[str, object]:
        return {
            "stage": self.stage,
            "elapsed_ms": self.elapsed_ms,
            "peak_memory_kb": self.peak_memory_kb,
            "iterations": self.iterations,
        }


@dataclass(frozen=True)
class BuildProfile:
    enabled: bool
    iterations: int
    metrics: tuple[StageMetric, ...]
    manifest_bytes: int
    page_count: int
    element_count: int
    action_count: int

    def as_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "iterations": self.iterations,
            "metrics": [metric.as_dict() for metric in self.metrics],
            "manifest_bytes": self.manifest_bytes,
            "page_count": self.page_count,
            "element_count": self.element_count,
            "action_count": self.action_count,
        }


def profile_app_build(
    app_path: str | Path,
    *,
    iterations: int = 1,
    enabled: bool = True,
) -> BuildProfile:
    if iterations < 1:
        raise Namel3ssError("Profiling iterations must be >= 1.")
    path = _resolve_app_path(app_path)
    if not enabled:
        return BuildProfile(
            enabled=False,
            iterations=iterations,
            metrics=tuple(
                StageMetric(stage=stage, elapsed_ms=0.0, peak_memory_kb=0, iterations=iterations)
                for stage in _STAGE_ORDER
            ),
            manifest_bytes=0,
            page_count=0,
            element_count=0,
            action_count=0,
        )

    totals_ms: dict[str, float] = {stage: 0.0 for stage in _STAGE_ORDER}
    peaks_kb: dict[str, int] = {stage: 0 for stage in _STAGE_ORDER}
    manifest_payload: dict[str, object] = {}
    serialized_manifest = ""

    for _ in range(iterations):
        (program, _sources), load_ms, load_peak = _measure(lambda: load_program(path.as_posix()))
        totals_ms["load_program"] += load_ms
        peaks_kb["load_program"] = max(peaks_kb["load_program"], load_peak)

        config = load_config(app_path=path)
        manifest_payload, manifest_ms, manifest_peak = _measure(
            lambda: build_static_manifest(program, config=config, state={}, store=None, warnings=[])
        )
        totals_ms["build_manifest"] += manifest_ms
        peaks_kb["build_manifest"] = max(peaks_kb["build_manifest"], manifest_peak)

        serialized_manifest, serialize_ms, serialize_peak = _measure(
            lambda: canonical_json_dumps(manifest_payload, pretty=True, drop_run_keys=False)
        )
        totals_ms["serialize_manifest"] += serialize_ms
        peaks_kb["serialize_manifest"] = max(peaks_kb["serialize_manifest"], serialize_peak)

    metrics = tuple(
        StageMetric(
            stage=stage,
            elapsed_ms=round(totals_ms[stage] / iterations, 6),
            peak_memory_kb=peaks_kb[stage],
            iterations=iterations,
        )
        for stage in _STAGE_ORDER
    )
    manifest_bytes = len(serialized_manifest.encode("utf-8"))
    page_count, element_count = _manifest_shape(manifest_payload)
    action_count = _action_count(manifest_payload)
    return BuildProfile(
        enabled=True,
        iterations=iterations,
        metrics=metrics,
        manifest_bytes=manifest_bytes,
        page_count=page_count,
        element_count=element_count,
        action_count=action_count,
    )


def _measure(callable_fn: Callable[[], object]) -> tuple[object, float, int]:
    tracemalloc.start()
    start = time.perf_counter_ns()
    try:
        result = callable_fn()
    finally:
        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000.0
        _, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    return result, elapsed_ms, int(peak_bytes // 1024)


def _resolve_app_path(value: str | Path) -> Path:
    path = Path(value).expanduser().resolve()
    if path.suffix != ".ai":
        raise Namel3ssError("Profiler requires an app.ai input file.")
    if not path.exists() or not path.is_file():
        raise Namel3ssError(f"Profiler input was not found: {path.as_posix()}")
    return path


def _manifest_shape(manifest_payload: Mapping[str, object]) -> tuple[int, int]:
    raw_pages = manifest_payload.get("pages")
    pages = raw_pages if isinstance(raw_pages, list) else []
    element_count = 0
    for page in pages:
        if not isinstance(page, Mapping):
            continue
        element_count += _count_elements_for_page(page)
    return len(pages), element_count


def _count_elements_for_page(page: Mapping[str, object]) -> int:
    total = 0
    raw_elements = page.get("elements")
    if isinstance(raw_elements, list):
        total += _count_elements(raw_elements)

    raw_layout = page.get("layout")
    if isinstance(raw_layout, Mapping):
        for key in sorted(str(item) for item in raw_layout.keys()):
            original_key = _resolve_original_key(raw_layout, key)
            if original_key is None:
                continue
            slot_value = raw_layout[original_key]
            if isinstance(slot_value, list):
                total += _count_elements(slot_value)

    diagnostics_blocks = page.get("diagnostics_blocks")
    if isinstance(diagnostics_blocks, list):
        total += _count_elements(diagnostics_blocks)
    return total


def _count_elements(items: Iterable[object]) -> int:
    total = 0
    for item in items:
        if not isinstance(item, Mapping):
            continue
        if isinstance(item.get("type"), str):
            total += 1
        nested_children = item.get("children")
        if isinstance(nested_children, list):
            total += _count_elements(nested_children)
    return total


def _action_count(manifest_payload: Mapping[str, object]) -> int:
    raw_actions = manifest_payload.get("actions")
    if isinstance(raw_actions, Mapping):
        return len(raw_actions)
    return 0


def _resolve_original_key(mapping: Mapping[str, object], key_text: str) -> str | None:
    for key in mapping.keys():
        if str(key) == key_text:
            return key
    return None


__all__ = [
    "BuildProfile",
    "StageMetric",
    "profile_app_build",
]
