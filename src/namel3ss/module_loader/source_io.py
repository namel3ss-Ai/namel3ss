from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from typing import Dict, Tuple

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.core import parse


ParseCache = Dict[Path, Tuple[str, ast.Program]]
SourceOverrides = Dict[Path, str]


def _read_source(path: Path, source_overrides: SourceOverrides | None) -> str:
    if _has_override(path, source_overrides):
        return source_overrides[path]  # type: ignore[index]
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as err:
        raise Namel3ssError(f"File not found: {path}") from err


def _parse_source(
    source: str,
    path: Path,
    *,
    allow_legacy_type_aliases: bool,
    allow_capsule: bool = False,
    require_spec: bool = True,
    lower_sugar: bool = True,
    parse_cache: ParseCache | None = None,
) -> ast.Program:
    digest = _source_digest(source)
    if parse_cache is not None:
        cached = parse_cache.get(path)
        if cached and cached[0] == digest:
            return copy.deepcopy(cached[1])
    try:
        parsed = parse(
            source,
            allow_legacy_type_aliases=allow_legacy_type_aliases,
            allow_capsule=allow_capsule,
            require_spec=require_spec,
            lower_sugar=lower_sugar,
        )
        if parse_cache is not None:
            parse_cache[path] = (digest, copy.deepcopy(parsed))
        return parsed
    except Namel3ssError as err:
        raise Namel3ssError(
            err.message,
            line=err.line,
            column=err.column,
            end_line=err.end_line,
            end_column=err.end_column,
            details={"file": path.as_posix()},
        ) from err


def _has_override(path: Path, source_overrides: SourceOverrides | None) -> bool:
    if not source_overrides:
        return False
    return path in source_overrides


def _source_digest(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


__all__ = ["ParseCache", "SourceOverrides", "_has_override", "_parse_source", "_read_source"]
