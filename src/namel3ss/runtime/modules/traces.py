from __future__ import annotations

from typing import Iterable, List

from namel3ss.runtime.modules.format import ModuleLoadResult, ModuleOverride
from namel3ss.runtime.modules.render import (
    render_module_loaded,
    render_module_merged,
    render_module_overrides,
)
from namel3ss.traces.schema import TRACE_VERSION, TraceEventType


def build_module_loaded(module: ModuleLoadResult) -> dict:
    return {
        "type": TraceEventType.MODULE_LOADED,
        "trace_version": TRACE_VERSION,
        "module_path": module.module_id,
        "module_alias": module.alias,
        "title": "module loaded",
        "lines": render_module_loaded(module),
    }


def build_module_merged(modules: Iterable[ModuleLoadResult]) -> dict:
    return {
        "type": TraceEventType.MODULE_MERGED,
        "trace_version": TRACE_VERSION,
        "title": "modules merged",
        "lines": render_module_merged(modules),
    }


def build_module_overrides(overrides: Iterable[ModuleOverride]) -> dict:
    return {
        "type": TraceEventType.MODULE_OVERRIDES,
        "trace_version": TRACE_VERSION,
        "title": "module overrides",
        "lines": render_module_overrides(overrides),
    }


def build_module_traces(modules: List[ModuleLoadResult], overrides: List[ModuleOverride]) -> List[dict]:
    if not modules:
        return []
    traces: List[dict] = []
    for module in modules:
        traces.append(build_module_loaded(module))
    traces.append(build_module_merged(modules))
    traces.append(build_module_overrides(overrides))
    return traces


__all__ = [
    "build_module_loaded",
    "build_module_merged",
    "build_module_overrides",
    "build_module_traces",
]
