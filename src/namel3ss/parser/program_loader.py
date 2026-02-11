from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError


@dataclass(frozen=True)
class IncludeProgramEntry:
    include_index: int
    path: Path
    path_norm: str
    program: ast.Program
    line: int | None
    column: int | None


@dataclass(frozen=True)
class IncludeWarning:
    code: str
    message: str
    file: str
    line: int | None
    column: int | None


@dataclass(frozen=True)
class IncludeExpansionResult:
    entries: tuple[IncludeProgramEntry, ...]
    warnings: tuple[IncludeWarning, ...]


def load_included_programs(
    *,
    root_program: ast.Program,
    root_file: Path,
    read_source: Callable[[Path], str],
    parse_source: Callable[[str, Path], ast.Program],
) -> IncludeExpansionResult:
    root_dir = root_file.resolve().parent
    includes = list(getattr(root_program, "includes", []) or [])
    if not includes:
        return IncludeExpansionResult(entries=(), warnings=())

    ordered: list[IncludeProgramEntry] = []
    warnings: list[IncludeWarning] = []
    seen: dict[str, IncludeProgramEntry] = {}
    visiting: list[str] = []

    def visit(include_decl: ast.IncludeDecl) -> None:
        include_path = _resolve_include_target(
            root_dir,
            include_decl.path_norm or include_decl.path_raw,
            line=include_decl.line,
            column=include_decl.column,
        )
        path_norm = include_path.relative_to(root_dir).as_posix()
        if path_norm in visiting:
            cycle_start = visiting.index(path_norm)
            cycle_nodes = [*visiting[cycle_start:], path_norm]
            raise Namel3ssError(f"Compile error: include cycle detected: {' -> '.join(cycle_nodes)}")
        if path_norm in seen:
            warnings.append(
                IncludeWarning(
                    code="composition.duplicate_include",
                    message=f'Warning: Duplicate include ignored: "{path_norm}"',
                    file=root_file.name,
                    line=include_decl.line,
                    column=include_decl.column,
                )
            )
            return
        source = read_source(include_path)
        try:
            program = parse_source(source, include_path)
        except Namel3ssError as err:
            details = dict(err.details) if isinstance(err.details, dict) else {}
            details["file"] = path_norm
            raise Namel3ssError(
                err.message,
                line=err.line,
                column=err.column,
                end_line=err.end_line,
                end_column=err.end_column,
                details=details,
            ) from err
        entry = IncludeProgramEntry(
            include_index=len(ordered),
            path=include_path,
            path_norm=path_norm,
            program=program,
            line=include_decl.line,
            column=include_decl.column,
        )
        seen[path_norm] = entry
        ordered.append(entry)
        visiting.append(path_norm)
        for child in list(getattr(program, "includes", []) or []):
            visit(child)
        visiting.pop()

    for include_decl in includes:
        visit(include_decl)

    warnings.sort(key=lambda item: (item.file, item.line or 0, item.column or 0, item.code, item.message))
    return IncludeExpansionResult(
        entries=tuple(ordered),
        warnings=tuple(warnings),
    )


def _resolve_include_target(root_dir: Path, include_path: str, *, line: int | None, column: int | None) -> Path:
    normalized = str(include_path or "").replace("\\", "/").strip()
    if not normalized:
        raise Namel3ssError("Compile error: include path cannot be empty.", line=line, column=column)
    candidate = Path(normalized)
    if candidate.is_absolute() or candidate.drive:
        raise Namel3ssError(
            "Compile error: include paths must be relative to the root app file.",
            line=line,
            column=column,
        )
    if ".." in candidate.parts:
        raise Namel3ssError(
            "Compile error: include paths cannot contain '..'.",
            line=line,
            column=column,
        )
    if candidate.suffix != ".ai":
        raise Namel3ssError(
            "Compile error: include paths must end with .ai.",
            line=line,
            column=column,
        )
    resolved = (root_dir / candidate).resolve()
    try:
        resolved.relative_to(root_dir)
    except ValueError as err:
        raise Namel3ssError(
            "Compile error: include path escapes the project root.",
            line=line,
            column=column,
        ) from err
    if not resolved.exists():
        rel = resolved.relative_to(root_dir).as_posix()
        raise Namel3ssError(
            f'Compile error: included file not found: "{rel}"',
            line=line,
            column=column,
        )
    return resolved


__all__ = [
    "IncludeExpansionResult",
    "IncludeProgramEntry",
    "IncludeWarning",
    "load_included_programs",
]
