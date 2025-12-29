from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.runtime.modules.format import ModuleLoadResult, ModuleMergeResult, ModuleOverride, SourceInfo
from namel3ss.runtime.modules.sources import source_for_main, source_for_module


_PLURAL_CATEGORY = {
    "function": "functions",
    "record": "records",
    "tool": "tools",
    "page": "pages",
}


def merge_modules(program: ir.Program, modules: List[ModuleLoadResult], *, app_path: Path) -> ModuleMergeResult:
    sources: Dict[Tuple[str, str], SourceInfo] = {}
    overrides: List[ModuleOverride] = []

    main_source = source_for_main(app_path)
    records = list(program.records)
    record_index = {rec.name: idx for idx, rec in enumerate(records)}
    pages = list(program.pages)
    page_index = {page.name: idx for idx, page in enumerate(pages)}
    functions = dict(program.functions)
    tools = dict(program.tools)

    for name in functions.keys():
        sources[("function", name)] = main_source
    for rec in records:
        sources[("record", rec.name)] = main_source
    for tool_name in tools.keys():
        sources[("tool", tool_name)] = main_source
    for page in pages:
        sources[("page", page.name)] = main_source

    for module in modules:
        module_source = source_for_module(module)
        allow_override = set(module.selection.allow_override)
        module_records = {rec.name: rec for rec in module.program.records}
        module_pages = {page.name: page for page in module.program.pages}
        module_functions = module.program.functions
        module_tools = module.program.tools
        for category, names in module.provided.items():
            if category == "functions":
                for name in names:
                    if name in functions:
                        _apply_override(
                            category="function",
                            name=name,
                            allow_override=allow_override,
                            sources=sources,
                            overrides=overrides,
                            previous_source=sources.get(("function", name), main_source),
                            current_source=module_source,
                            module=module,
                        )
                    functions[name] = module_functions[name]
                    sources[("function", name)] = module_source
            elif category == "records":
                for name in names:
                    if name in record_index:
                        _apply_override(
                            category="record",
                            name=name,
                            allow_override=allow_override,
                            sources=sources,
                            overrides=overrides,
                            previous_source=sources.get(("record", name), main_source),
                            current_source=module_source,
                            module=module,
                        )
                        records, record_index = _replace_list_item(records, record_index, name, module_records[name])
                    else:
                        records.append(module_records[name])
                        record_index[name] = len(records) - 1
                    sources[("record", name)] = module_source
            elif category == "tools":
                for name in names:
                    if name in tools:
                        _apply_override(
                            category="tool",
                            name=name,
                            allow_override=allow_override,
                            sources=sources,
                            overrides=overrides,
                            previous_source=sources.get(("tool", name), main_source),
                            current_source=module_source,
                            module=module,
                        )
                    tools[name] = module_tools[name]
                    sources[("tool", name)] = module_source
            elif category == "pages":
                for name in names:
                    if name in page_index:
                        _apply_override(
                            category="page",
                            name=name,
                            allow_override=allow_override,
                            sources=sources,
                            overrides=overrides,
                            previous_source=sources.get(("page", name), main_source),
                            current_source=module_source,
                            module=module,
                        )
                        pages, page_index = _replace_list_item(pages, page_index, name, module_pages[name])
                    else:
                        pages.append(module_pages[name])
                        page_index[name] = len(pages) - 1
                    sources[("page", name)] = module_source

    program.records = records
    program.pages = pages
    program.functions = functions
    program.tools = tools

    return ModuleMergeResult(
        program=program,
        sources=sources,
        modules=modules,
        overrides=overrides,
    )


def _apply_override(
    *,
    category: str,
    name: str,
    allow_override: set[str],
    sources: Dict[Tuple[str, str], SourceInfo],
    overrides: List[ModuleOverride],
    previous_source: SourceInfo,
    current_source: SourceInfo,
    module: ModuleLoadResult,
) -> None:
    allow_key = _PLURAL_CATEGORY.get(category, category)
    if allow_key not in allow_override:
        raise Namel3ssError(
            build_guidance_message(
                what=f"{category} name {name} already exists.",
                why="Module imports cannot overwrite existing names.",
                fix=f"Allow override for {category} or rename the {category}.",
                example=f'use module "{module.module_id}" as {module.alias}\nallow override:\n  {allow_key}',
            )
        )
    overrides.append(
        ModuleOverride(
            kind=category,
            name=name,
            previous=previous_source,
            current=current_source,
        )
    )


def _replace_list_item(
    items: List, index: Dict[str, int], name: str, value
) -> tuple[List, Dict[str, int]]:
    remove_at = index.get(name)
    if remove_at is None:
        items.append(value)
        index[name] = len(items) - 1
        return items, index
    items.pop(remove_at)
    next_index: Dict[str, int] = {}
    for idx, item in enumerate(items):
        next_index[getattr(item, "name", "")] = idx
    items.append(value)
    next_index[name] = len(items) - 1
    return items, next_index


__all__ = ["merge_modules"]
