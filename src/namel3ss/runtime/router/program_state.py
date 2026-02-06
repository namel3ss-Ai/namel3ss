from __future__ import annotations

import hashlib
from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.errors.base import Namel3ssError


class ProgramState:
    def __init__(self, app_path: Path) -> None:
        self.app_path = Path(app_path).resolve()
        self.project_root = self.app_path.parent
        self.program = None
        self.sources: dict[Path, str] = {}
        self.revision = ""
        self.error: Namel3ssError | None = None
        self._watch_snapshot: dict[Path, tuple[int, int]] = {}
        self._load_program()

    def refresh_if_needed(self) -> bool:
        if not self._should_reload():
            return False
        try:
            self._load_program()
            return True
        except Namel3ssError as err:
            self.error = err
            return False

    def _load_program(self) -> None:
        program, sources = load_program(self.app_path.as_posix())
        self.program = program
        self.sources = sources
        self.revision = _compute_revision(sources)
        self._watch_snapshot = _snapshot_paths(list(sources.keys()))
        self.error = None

    def _should_reload(self) -> bool:
        watch_paths = self._watch_paths()
        snapshot = _snapshot_paths(watch_paths)
        if not self._watch_snapshot:
            self._watch_snapshot = snapshot
            return True
        if snapshot != self._watch_snapshot:
            self._watch_snapshot = snapshot
            return True
        return False

    def _watch_paths(self) -> list[Path]:
        if self.sources:
            return sorted(self.sources.keys(), key=lambda p: p.as_posix())
        return _scan_project_sources(self.project_root)


def _scan_project_sources(project_root: Path) -> list[Path]:
    paths: list[Path] = []
    for path in sorted(project_root.rglob("*.ai"), key=lambda p: p.as_posix()):
        if ".namel3ss" in path.parts:
            continue
        paths.append(path)
    return paths or [project_root / "app.ai"]


def _snapshot_paths(paths: list[Path]) -> dict[Path, tuple[int, int]]:
    snapshot: dict[Path, tuple[int, int]] = {}
    for path in paths:
        try:
            stat = path.stat()
            snapshot[path] = (stat.st_mtime_ns, stat.st_size)
        except FileNotFoundError:
            snapshot[path] = (-1, -1)
    return snapshot


def _compute_revision(sources: dict[Path, str]) -> str:
    digest = hashlib.sha256()
    for path, text in sorted(sources.items(), key=lambda item: item[0].as_posix()):
        digest.update(path.as_posix().encode("utf-8"))
        digest.update(text.encode("utf-8"))
    return digest.hexdigest()[:12]


__all__ = ["ProgramState"]
