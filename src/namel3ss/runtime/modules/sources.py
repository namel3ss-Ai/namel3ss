from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

from namel3ss.runtime.modules.format import ModuleLoadResult, SourceInfo


def source_for_main(app_path: Path) -> SourceInfo:
    return SourceInfo(
        origin="main",
        file_path=app_path.as_posix(),
        module_path=None,
        module_alias=None,
    )


def source_for_module(module: ModuleLoadResult) -> SourceInfo:
    return SourceInfo(
        origin="module",
        file_path=module.path.as_posix(),
        module_path=module.module_id,
        module_alias=module.alias,
    )


def source_info_dict(info: SourceInfo) -> dict:
    return {
        "origin": info.origin,
        "file_path": info.file_path,
        "module_path": info.module_path,
        "module_alias": info.module_alias,
    }


def flatten_sources(sources: Dict[Tuple[str, str], SourceInfo]) -> List[dict]:
    entries: List[dict] = []
    for key in sorted(sources.keys()):
        kind, name = key
        info = sources[key]
        entries.append(
            {
                "kind": kind,
                "name": name,
                "origin": info.origin,
                "file_path": info.file_path,
                "module_path": info.module_path,
                "module_alias": info.module_alias,
            }
        )
    return entries


__all__ = ["flatten_sources", "source_for_main", "source_for_module", "source_info_dict"]
