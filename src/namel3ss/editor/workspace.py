from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable

from namel3ss.module_loader import load_project
from namel3ss.module_loader.source_io import ParseCache, SourceOverrides


def normalize_path(path: Path, root: Path) -> str:
    resolved = _safe_resolve(path)
    root_resolved = _safe_resolve(root)
    try:
        rel = resolved.relative_to(root_resolved)
        return rel.as_posix()
    except ValueError:
        return resolved.as_posix()


def _safe_resolve(path: Path) -> Path:
    try:
        return path.resolve()
    except FileNotFoundError:
        return path.absolute()


def is_test_path(path: Path) -> bool:
    lower_parts = {part.lower() for part in path.parts}
    if "tests" in lower_parts:
        return True
    if path.name.endswith("_test.ai"):
        return True
    return False


def collect_project_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    files: list[Path] = []
    for path in root.rglob("*.ai"):
        if is_test_path(path):
            continue
        files.append(path)
    return sorted({p.resolve() for p in files}, key=lambda p: p.as_posix())


@dataclass
class EditorWorkspace:
    app_path: Path
    root: Path
    parse_cache: ParseCache = field(default_factory=dict)

    @classmethod
    def from_app_path(cls, app_path: str | Path) -> "EditorWorkspace":
        app_path = _safe_resolve(Path(app_path))
        return cls(app_path=app_path, root=_safe_resolve(app_path.parent))

    def build_overrides(self, files: Dict[str, str] | None) -> SourceOverrides:
        overrides: SourceOverrides = {}
        if not files:
            return overrides
        for raw_path, content in files.items():
            path = Path(raw_path)
            if not path.is_absolute():
                path = (self.root / path).resolve()
            overrides[path] = content
        return overrides

    def load(self, overrides: SourceOverrides | None = None, *, allow_legacy_type_aliases: bool = True):
        return load_project(
            self.app_path,
            allow_legacy_type_aliases=allow_legacy_type_aliases,
            source_overrides=overrides,
            parse_cache=self.parse_cache,
        )


__all__ = ["EditorWorkspace", "collect_project_files", "normalize_path", "is_test_path"]
