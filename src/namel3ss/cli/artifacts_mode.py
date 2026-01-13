from __future__ import annotations

import json
import shutil
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


@dataclass(frozen=True)
class ArtifactState:
    artifacts_dir: Path
    exists: bool
    size_bytes: int | None
    last_outcome: str
    last_timestamp: datetime | None


def run_artifacts_status(args: list[str]) -> int:
    _ensure_no_extra_args(args, command="status")
    root = _discover_root()
    artifacts_dir = root / ".namel3ss"
    state = _inspect_artifacts(artifacts_dir)
    lines = ["namel3ss - status", ""]
    if not state.exists:
        lines.append("No runtime artifacts found.")
        print("\n".join(lines))
        return 0
    timestamp_text = _format_timestamp(state.last_timestamp)
    last_run_line = f"Last run: {state.last_outcome}"
    if timestamp_text:
        last_run_line = f"{last_run_line} ({timestamp_text})"
    lines.extend(
        [
            last_run_line,
            "Artifacts present: yes",
            f"Size: {_format_size(state.size_bytes)}",
            f"Location: {_display_path(state.artifacts_dir)}",
        ]
    )
    print("\n".join(lines))
    return 0


def run_artifacts_clean(args: list[str]) -> int:
    yes = False
    extra_args = []
    for arg in args:
        if arg == "--yes":
            yes = True
        elif arg:
            extra_args.append(arg)
    if extra_args:
        raise Namel3ssError(
            build_guidance_message(
                what="Unknown arguments for clean.",
                why="clean only supports the --yes flag.",
                fix="Remove extra arguments and re-run.",
                example="n3 clean --yes",
            )
        )
    root = _discover_root()
    artifacts_dir = root / ".namel3ss"
    state = _inspect_artifacts(artifacts_dir)
    if not state.exists:
        print("No runtime artifacts found.")
        return 0
    size_text = _format_size(state.size_bytes)
    target_line = f"• {_display_path(state.artifacts_dir)}"
    if size_text:
        target_line = f"{target_line} ({size_text})"
    print("This will remove the namel3ss runtime artifacts:")
    print(target_line)
    print()
    if not yes:
        response = input("Safe to delete. Continue? (y/N) ").strip().lower()
        if response not in {"y", "yes"}:
            print("Aborted.")
            return 0
    _remove_artifacts(artifacts_dir)
    print("Removed namel3ss runtime artifacts.")
    return 0


def _ensure_no_extra_args(args: list[str], *, command: str) -> None:
    extras = [arg for arg in args if arg]
    if extras:
        raise Namel3ssError(
            build_guidance_message(
                what="Unexpected arguments.",
                why=f"{command} does not take any arguments or flags.",
                fix="Re-run without extra values.",
                example=f"n3 {command}",
            )
        )


def _discover_root() -> Path:
    cwd = Path.cwd()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / "app.ai").exists() or (candidate / ".namel3ss").exists():
            return candidate
    return cwd


def _inspect_artifacts(artifacts_dir: Path) -> ArtifactState:
    if not artifacts_dir.exists():
        return ArtifactState(artifacts_dir=artifacts_dir, exists=False, size_bytes=None, last_outcome="unknown", last_timestamp=None)
    size_bytes = _folder_size(artifacts_dir)
    outcome, timestamp = _read_last_outcome(artifacts_dir)
    if not timestamp:
        timestamp = _latest_timestamp(artifacts_dir)
    return ArtifactState(
        artifacts_dir=artifacts_dir,
        exists=True,
        size_bytes=size_bytes,
        last_outcome=outcome,
        last_timestamp=timestamp,
    )


def _read_last_outcome(artifacts_dir: Path) -> tuple[str, datetime | None]:
    outcome_path = artifacts_dir / "outcome" / "last.json"
    if outcome_path.exists():
        status = _extract_status(outcome_path)
        return status, _safe_mtime(outcome_path, follow_symlinks=False)
    errors_path = artifacts_dir / "errors" / "last.json"
    if errors_path.exists():
        status = _extract_status(errors_path)
        normalized = status if status != "unknown" else "failed"
        return normalized, _safe_mtime(errors_path, follow_symlinks=False)
    return "unknown", None


def _extract_status(path: Path) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return "unknown"
    if isinstance(payload, dict):
        status = payload.get("status")
        if not status:
            outcome = payload.get("outcome")
            if isinstance(outcome, dict):
                status = outcome.get("status")
        return _normalize_status(status)
    return "unknown"


def _normalize_status(value: str | None) -> str:
    if value is None:
        return "unknown"
    lowered = str(value).strip().lower()
    if lowered in {"ok", "success", "succeeded"}:
        return "success"
    if lowered in {"error", "failed", "failure"}:
        return "failed"
    if lowered == "partial":
        return "partial"
    return "unknown"


def _folder_size(path: Path) -> int | None:
    try:
        if path.is_symlink():
            return path.stat(follow_symlinks=False).st_size
        if path.is_file():
            return path.stat(follow_symlinks=False).st_size
    except OSError:
        return None
    total = 0
    for root, _, files in os.walk(path, followlinks=False):
        root_path = Path(root)
        for name in files:
            file_path = root_path / name
            try:
                total += file_path.stat(follow_symlinks=False).st_size
            except OSError:
                continue
    return total


def _latest_timestamp(path: Path) -> datetime | None:
    latest = _safe_mtime(path, follow_symlinks=False)
    if not path.is_dir():
        return latest
    for root, dirs, files in os.walk(path, followlinks=False):
        root_path = Path(root)
        for name in files:
            candidate = _safe_mtime(root_path / name, follow_symlinks=False)
            if candidate and (latest is None or candidate > latest):
                latest = candidate
        for dirname in dirs:
            candidate = _safe_mtime(root_path / dirname, follow_symlinks=False)
            if candidate and (latest is None or candidate > latest):
                latest = candidate
    return latest


def _safe_mtime(path: Path, *, follow_symlinks: bool = True) -> datetime | None:
    try:
        ts = path.stat(follow_symlinks=follow_symlinks).st_mtime
    except OSError:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def _format_size(size_bytes: int | None) -> str:
    if size_bytes is None:
        return "unknown size"
    size = float(size_bytes)
    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{int(size_bytes)} B"


def _format_timestamp(timestamp: datetime | None) -> str:
    if not timestamp:
        return "unknown time"
    local_time = timestamp.astimezone()
    return local_time.strftime("%Y-%m-%d %H:%M:%S %Z").strip()


def _display_path(path: Path) -> str:
    try:
        relative = path.relative_to(Path.cwd())
        return relative.as_posix()
    except ValueError:
        return path.as_posix()


def _remove_artifacts(artifacts_dir: Path) -> None:
    if artifacts_dir.is_symlink():
        artifacts_dir.unlink(missing_ok=True)
        return
    if artifacts_dir.is_dir():
        shutil.rmtree(artifacts_dir)
        return
    if artifacts_dir.exists():
        artifacts_dir.unlink()


__all__ = ["run_artifacts_clean", "run_artifacts_status"]
