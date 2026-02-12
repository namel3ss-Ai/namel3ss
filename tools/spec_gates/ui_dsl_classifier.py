from __future__ import annotations

from pathlib import PurePosixPath


_SEMANTIC_PREFIXES: tuple[str, ...] = (
    "src/namel3ss/parser/",
    "src/namel3ss/ast/",
    "src/namel3ss/ir/",
    "src/namel3ss/ui/manifest/",
)

_SEMANTIC_FILES: tuple[str, ...] = (
    "tools/generate_parser.py",
)


def normalize_repo_path(path: str) -> str:
    text = str(path or "").strip().replace("\\", "/")
    if not text:
        return ""
    return PurePosixPath(text).as_posix()


def is_ui_dsl_semantic_path(path: str) -> bool:
    normalized = normalize_repo_path(path)
    if not normalized:
        return False
    if normalized in _SEMANTIC_FILES:
        return True
    return any(normalized.startswith(prefix) for prefix in _SEMANTIC_PREFIXES)


def classify_ui_dsl_semantic_files(paths: list[str] | tuple[str, ...]) -> list[str]:
    offenders = [normalize_repo_path(path) for path in paths if is_ui_dsl_semantic_path(path)]
    return sorted({path for path in offenders if path})


__all__ = [
    "classify_ui_dsl_semantic_files",
    "is_ui_dsl_semantic_path",
    "normalize_repo_path",
]
