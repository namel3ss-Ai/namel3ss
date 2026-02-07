from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.module_loader.source_io import ParseCache, SourceOverrides, _has_override, _parse_source, _read_source
from namel3ss.module_loader.types import ModuleExports, ModuleInfo


def _load_module(
    module_name: str,
    root: Path,
    modules: Dict[str, ModuleInfo],
    sources: Dict[Path, str],
    *,
    allow_legacy_type_aliases: bool,
    source_overrides: SourceOverrides | None,
    parse_cache: ParseCache | None,
) -> None:
    if module_name in modules:
        return
    module_dir, capsule_path = _resolve_module_dir(root, module_name, source_overrides)
    capsule_source = _read_source(capsule_path, source_overrides)
    sources[capsule_path] = capsule_source
    capsule_program = _parse_source(
        capsule_source,
        capsule_path,
        allow_legacy_type_aliases=allow_legacy_type_aliases,
        allow_capsule=True,
        require_spec=False,
        parse_cache=parse_cache,
    )
    if capsule_program.capsule is None:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Capsule file for '{module_name}' is missing a capsule declaration.",
                why="Each module must declare its capsule name and exports.",
                fix='Add `capsule "<name>":` and an exports block.',
                example=f'capsule "{module_name}":',
            )
        )
    capsule_decl = capsule_program.capsule
    if capsule_decl.name != module_name:
        raise Namel3ssError(
            build_guidance_message(
                what="Capsule name does not match module folder.",
                why=f'capsule.ai declares "{capsule_decl.name}" but the folder is "{module_name}".',
                fix="Update the capsule name to match the folder.",
                example=f'capsule "{module_name}":',
            ),
            line=capsule_decl.line,
            column=capsule_decl.column,
        )
    programs = []
    files = _collect_module_files(module_dir, source_overrides)
    for path in files:
        source = _read_source(path, source_overrides)
        sources[path] = source
        program = _parse_source(
            source,
            path,
            allow_legacy_type_aliases=allow_legacy_type_aliases,
            require_spec=False,
            parse_cache=parse_cache,
        )
        if program.app_theme_line is not None:
            raise Namel3ssError(
                build_guidance_message(
                    what="App declarations are not allowed inside modules.",
                    why="Only the root app.ai file defines the app theme and UI shell.",
                    fix="Move the app declaration to app.ai.",
                    example="app:\n  theme is \"system\"",
                ),
                line=program.app_theme_line,
                column=program.app_theme_column,
            )
        if getattr(program, "theme_line", None) is not None:
            raise Namel3ssError(
                build_guidance_message(
                    what="Theme declarations are not allowed inside modules.",
                    why="Only the root app.ai file defines global theming.",
                    fix="Move the theme block to app.ai.",
                    example='theme:\n  preset: "clarity"',
                ),
                line=getattr(program, "theme_line", None),
                column=getattr(program, "theme_column", None),
            )
        if getattr(program, "ui_line", None) is not None:
            raise Namel3ssError(
                build_guidance_message(
                    what="UI declarations are not allowed inside modules.",
                    why="Global ui settings belong in app.ai only.",
                    fix="Move the ui block to app.ai.",
                    example='ui:\n  theme is "light"\n  accent color is "blue"',
                ),
                line=program.ui_line,
                column=program.ui_column,
            )
        programs.append(program)

    uses = list(capsule_program.uses)
    for program in programs:
        uses.extend(program.uses)
    module_file_uses = [use for use in uses if use.module_path]
    if module_file_uses:
        first = module_file_uses[0]
        raise Namel3ssError(
            build_guidance_message(
                what="Use module is not allowed inside capsule modules.",
                why="Capsule modules only import other capsules.",
                fix="Move use module statements to app.ai.",
                example='use module "modules/common.ai" as common',
            ),
            line=first.line,
            column=first.column,
        )
    uses = [use for use in uses if not use.module_path]

    exports = ModuleExports()
    for export in capsule_decl.exports:
        exports.add(export.kind, export.name)

    modules[module_name] = ModuleInfo(
        name=module_name,
        path=module_dir,
        capsule=capsule_decl,
        uses=uses,
        programs=programs,
        exports=exports,
        files=files,
    )

    for use in uses:
        _load_module(
            use.module,
            root,
            modules,
            sources,
            allow_legacy_type_aliases=allow_legacy_type_aliases,
            source_overrides=source_overrides,
            parse_cache=parse_cache,
        )


def _resolve_module_dir(root: Path, module_name: str, source_overrides: SourceOverrides | None) -> tuple[Path, Path]:
    module_dir = root / "modules" / module_name
    capsule_path = module_dir / "capsule.ai"
    if capsule_path.exists() or _has_override(capsule_path, source_overrides):
        return module_dir, capsule_path
    package_dir = root / "packages" / module_name
    package_capsule = package_dir / "capsule.ai"
    if package_capsule.exists() or _has_override(package_capsule, source_overrides):
        return package_dir, package_capsule
    raise Namel3ssError(
        build_guidance_message(
            what=f"Module '{module_name}' was not found.",
            why=(
                f"No capsule.ai exists at {capsule_path.as_posix()} "
                f"or {package_capsule.as_posix()}."
            ),
            fix=f"Create modules/{module_name}/capsule.ai or install the package.",
            example=f'modules/{module_name}/capsule.ai',
        )
    )


def _collect_module_files(module_dir: Path, source_overrides: SourceOverrides | None) -> List[Path]:
    files = []
    for path in module_dir.rglob("*.ai"):
        if path.name in {"capsule.ai", "app.ai"}:
            continue
        if path.name.endswith("_test.ai"):
            continue
        relative_parts = {part.lower() for part in path.relative_to(module_dir).parts}
        if "tests" in relative_parts or "examples" in relative_parts or "example" in relative_parts:
            continue
        files.append(path)
    if source_overrides:
        for path in source_overrides.keys():
            if path.name in {"capsule.ai", "app.ai"} or path.suffix != ".ai":
                continue
            try:
                rel_parts = {part.lower() for part in path.relative_to(module_dir).parts}
            except ValueError:
                continue
            if "tests" in rel_parts or "examples" in rel_parts or "example" in rel_parts or path.name.endswith("_test.ai"):
                continue
            files.append(path)
    return sorted(files, key=lambda p: p.relative_to(module_dir).as_posix())


__all__ = ["_collect_module_files", "_load_module", "_resolve_module_dir"]
