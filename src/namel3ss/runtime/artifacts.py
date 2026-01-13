from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ARTIFACT_MODES = {"auto", "debug", "off"}
DEFAULT_KEEP_RUNS = 3
INDEX_FILENAME = "index.json"


def resolve_artifact_mode(cli_value: str | None) -> str:
    env_value = os.getenv("N3_ARTIFACT_MODE")
    value = cli_value or env_value or "auto"
    normalized = _normalize_mode(value)
    return normalized


def _normalize_mode(value: str) -> str:
    mode = str(value or "").strip().lower()
    if mode not in ARTIFACT_MODES:
        raise ValueError(f"Invalid artifact mode: {value!r}")
    return mode


def _normalize_status(value: str | None) -> str:
    text = str(value or "").strip().lower()
    if text in {"ok", "success", "succeeded", "pass"}:
        return "success"
    if text in {"error", "failed", "failure", "fail"}:
        return "failed"
    if text == "partial":
        return "partial"
    return "unknown"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _load_index(path: Path) -> dict:
    if not path.exists():
        return {"runs": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"runs": []}
    if not isinstance(data, dict):
        return {"runs": []}
    runs = data.get("runs")
    if not isinstance(runs, list):
        runs = []
    cleaned: list[dict] = []
    for entry in runs:
        if isinstance(entry, dict) and isinstance(entry.get("run_id"), int):
            cleaned.append(entry)
    return {"runs": cleaned}


def _write_index(path: Path, index: dict) -> None:
    payload = {"runs": sorted(index.get("runs", []), key=lambda item: item.get("run_id", 0))}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _next_run_id(index: dict) -> int:
    runs = index.get("runs") or []
    if not runs:
        return 1
    return max(entry.get("run_id", 0) for entry in runs if isinstance(entry, dict)) + 1


def _safe_remove(path: Path) -> None:
    try:
        if path.is_symlink() or path.is_file():
            path.unlink(missing_ok=True)
            return
        if path.is_dir():
            for root, dirs, files in os.walk(path, topdown=False, followlinks=False):
                root_path = Path(root)
                for name in files:
                    (root_path / name).unlink(missing_ok=True)
                for name in dirs:
                    candidate = root_path / name
                    if candidate.is_symlink():
                        candidate.unlink(missing_ok=True)
                    else:
                        candidate.rmdir()
            path.rmdir()
    except OSError:
        return


def _size_of_paths(root: Path, paths: Iterable[str]) -> int | None:
    total = 0
    for rel in paths:
        candidate = root / rel
        try:
            if candidate.is_symlink():
                total += candidate.stat(follow_symlinks=False).st_size
            elif candidate.is_file():
                total += candidate.stat(follow_symlinks=False).st_size
        except OSError:
            continue
    return total


@dataclass
class ArtifactRecorder:
    root: Path | None
    mode: str
    keep_runs: int = DEFAULT_KEEP_RUNS
    started_at: datetime = field(default_factory=_now)
    run_id: int | None = None
    _paths: set[str] = field(default_factory=set)
    _shared_paths: set[str] = field(default_factory=set)
    _index_cache: dict | None = None

    @property
    def allow_writes(self) -> bool:
        return self.mode != "off" and self.root is not None

    @property
    def allow_heavy(self) -> bool:
        return self.allow_writes and self.mode == "debug"

    def start_run(self) -> None:
        if not self.allow_writes:
            return
        self.root.mkdir(parents=True, exist_ok=True)
        index_path = self.root / INDEX_FILENAME
        self._index_cache = _load_index(index_path)
        self.run_id = _next_run_id(self._index_cache)

    def record_path(self, path: Path, *, shared: bool = False) -> None:
        if not self.allow_writes or self.root is None:
            return
        try:
            rel = path.relative_to(self.root).as_posix()
        except ValueError:
            return
        if shared:
            self._shared_paths.add(rel)
        else:
            self._paths.add(rel)

    def finalize_run(self, status: str) -> None:
        if not self.allow_writes or self.root is None:
            return
        index_path = self.root / INDEX_FILENAME
        index = self._index_cache or _load_index(index_path)
        run_id = self.run_id or _next_run_id(index)
        finished = _now()
        entry = {
            "run_id": run_id,
            "mode": self.mode,
            "started_at": _safe_iso(self.started_at),
            "finished_at": _safe_iso(finished),
            "status": _normalize_status(status),
            "paths": sorted(self._paths),
        }
        size = _size_of_paths(self.root, entry["paths"])
        if size is not None:
            entry["size_bytes"] = size
        index_runs = index.get("runs") or []
        index_runs = [run for run in index_runs if run.get("run_id") != run_id]
        index_runs.append(entry)
        index["runs"] = index_runs
        _write_index(index_path, index)
        self._enforce_retention(index_path, index, current_run_id=run_id)
        self._index_cache = index

    def _enforce_retention(self, index_path: Path, index: dict, *, current_run_id: int) -> None:
        runs = sorted(index.get("runs") or [], key=lambda r: r.get("run_id", 0))
        if len(runs) <= self.keep_runs:
            return
        latest_failure = None
        for entry in runs:
            if entry.get("status") == "failed":
                if latest_failure is None or entry.get("run_id", 0) > latest_failure.get("run_id", 0):
                    latest_failure = entry
        keep_ids = {run.get("run_id") for run in runs[-self.keep_runs :] if run.get("run_id") is not None}
        if latest_failure and latest_failure.get("run_id") is not None:
            keep_ids.add(latest_failure.get("run_id"))
        keep_ids.add(current_run_id)
        prunable = [run for run in runs if run.get("run_id") not in keep_ids]
        for entry in prunable:
            for rel in entry.get("paths") or []:
                self._delete_path(rel)
        kept = [run for run in runs if run.get("run_id") in keep_ids]
        index["runs"] = sorted(kept, key=lambda r: r.get("run_id", 0))
        _write_index(index_path, index)

    def _delete_path(self, rel: str) -> None:
        if self.root is None:
            return
        path = self.root / rel
        try:
            path.relative_to(self.root)
        except ValueError:
            return
        _safe_remove(path)


def load_index_entries(root: Path) -> list[dict]:
    path = root / INDEX_FILENAME
    return _load_index(path).get("runs", [])


__all__ = [
    "ARTIFACT_MODES",
    "DEFAULT_KEEP_RUNS",
    "INDEX_FILENAME",
    "ArtifactRecorder",
    "load_index_entries",
    "resolve_artifact_mode",
]
