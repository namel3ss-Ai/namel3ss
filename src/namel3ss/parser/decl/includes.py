from __future__ import annotations

from pathlib import PurePosixPath

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError

_INVALID_INCLUDE_MESSAGE = "include paths must be relative .ai files without '..'."


def parse_include_decl(parser) -> ast.IncludeDecl:
    include_tok = parser._advance()
    path_tok = parser._current()
    if path_tok.type != "STRING":
        raise _parse_include_error(path_tok.line, path_tok.column)
    raw_value = str(path_tok.value or "")
    parser._advance()
    normalized = _normalize_include_path(raw_value, line=path_tok.line, column=path_tok.column)
    return ast.IncludeDecl(
        path_raw=raw_value,
        path_norm=normalized,
        line=include_tok.line,
        column=include_tok.column,
    )


def _normalize_include_path(raw_value: str, *, line: int | None, column: int | None) -> str:
    text = str(raw_value or "").strip()
    if not text:
        raise _parse_include_error(line, column)
    normalized = text.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute():
        raise _parse_include_error(line, column)
    parts = list(path.parts)
    if not parts:
        raise _parse_include_error(line, column)
    if any(part in {"..", "."} for part in parts):
        raise _parse_include_error(line, column)
    if path.suffix != ".ai":
        raise _parse_include_error(line, column)
    return path.as_posix()


def _parse_include_error(line: int | None, column: int | None) -> Namel3ssError:
    line_value = line if isinstance(line, int) and line > 0 else 1
    col_value = column if isinstance(column, int) and column > 0 else 1
    return Namel3ssError(
        f"Parse error at line {line_value}, col {col_value}: {_INVALID_INCLUDE_MESSAGE}",
        line=line,
        column=column,
    )


__all__ = ["parse_include_decl"]
