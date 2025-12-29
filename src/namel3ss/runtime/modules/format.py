from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from namel3ss.ir import nodes as ir


MODULE_CATEGORIES = ("functions", "records", "tools", "pages")


@dataclass(frozen=True)
class ModuleSelection:
    only: tuple[str, ...]
    allow_override: tuple[str, ...]


@dataclass(frozen=True)
class SourceInfo:
    origin: str
    file_path: str | None
    module_path: str | None
    module_alias: str | None


@dataclass
class ModuleLoadResult:
    module_id: str
    module_name: str
    alias: str
    path: Path
    program: ir.Program
    provided: Dict[str, List[str]]
    selection: ModuleSelection


@dataclass(frozen=True)
class ModuleOverride:
    kind: str
    name: str
    previous: SourceInfo
    current: SourceInfo


@dataclass
class ModuleMergeResult:
    program: ir.Program
    sources: Dict[tuple[str, str], SourceInfo]
    modules: List[ModuleLoadResult]
    overrides: List[ModuleOverride]


__all__ = [
    "MODULE_CATEGORIES",
    "ModuleLoadResult",
    "ModuleMergeResult",
    "ModuleOverride",
    "ModuleSelection",
    "SourceInfo",
]
