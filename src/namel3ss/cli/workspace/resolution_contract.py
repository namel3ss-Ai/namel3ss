from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkspaceResolutionContract:
    search_root: Path
    selected_app_path: Path | None
    candidate_app_paths: tuple[Path, ...]
    alternative_app_paths: tuple[Path, ...]
    resolution_mode: str
    warning_required: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "alternative_app_paths": [path.as_posix() for path in self.alternative_app_paths],
            "candidate_app_paths": [path.as_posix() for path in self.candidate_app_paths],
            "resolution_mode": self.resolution_mode,
            "search_root": self.search_root.as_posix(),
            "selected_app_path": self.selected_app_path.as_posix() if isinstance(self.selected_app_path, Path) else "",
            "warning_required": bool(self.warning_required),
        }


__all__ = ["WorkspaceResolutionContract"]
