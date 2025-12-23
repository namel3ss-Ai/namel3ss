from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, Iterable, List

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.pkg.types import ChecksumEntry


def load_checksums(path: Path) -> Dict[str, str]:
    if not path.exists():
        raise Namel3ssError(
            build_guidance_message(
                what="Checksums manifest is missing.",
                why=f"Expected checksums file at {path.as_posix()}.",
                fix="Add a checksums.json file to the package.",
                example="checksums.json",
            )
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Checksums manifest is not valid JSON.",
                why=f"JSON parsing failed: {err.msg}.",
                fix="Fix the JSON in checksums.json.",
                example='{"files":{"capsule.ai":"sha256:..."}}',
            )
        ) from err
    files = data.get("files") if isinstance(data, dict) else None
    if files is None and isinstance(data, dict):
        files = data
    if not isinstance(files, dict):
        raise Namel3ssError(
            build_guidance_message(
                what="Checksums manifest has an invalid structure.",
                why="Expected a mapping of file paths to sha256 values.",
                fix="Use a JSON object with a files mapping.",
                example='{"files":{"capsule.ai":"sha256:..."}}',
            )
        )
    return {str(path): str(value) for path, value in files.items()}


def verify_checksums(package_root: Path, checksums_path: Path) -> List[ChecksumEntry]:
    manifest = load_checksums(checksums_path)
    expected_paths = set(manifest.keys())
    actual_paths = set(_list_files(package_root, exclude={checksums_path.relative_to(package_root).as_posix()}))
    missing = expected_paths - actual_paths
    extra = actual_paths - expected_paths
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing: {', '.join(sorted(missing))}")
        if extra:
            details.append(f"extra: {', '.join(sorted(extra))}")
        raise Namel3ssError(
            build_guidance_message(
                what="Checksums manifest does not match package contents.",
                why="Package files must match the checksums manifest; " + "; ".join(details) + ".",
                fix="Update checksums.json to match the package contents.",
                example='{"files":{"capsule.ai":"sha256:..."}}',
            )
        )
    entries: List[ChecksumEntry] = []
    for rel_path in sorted(actual_paths):
        file_path = package_root / rel_path
        digest = _sha256(file_path)
        expected = _normalize_checksum(manifest.get(rel_path))
        if digest != expected:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Checksum mismatch for {rel_path}.",
                    why="The file contents do not match the published checksum.",
                    fix="Redownload the package or update checksums.json.",
                    example="n3 pkg install",
                )
            )
        entries.append(ChecksumEntry(path=rel_path, sha256=digest))
    return entries


def _list_files(root: Path, *, exclude: Iterable[str]) -> List[str]:
    excluded = set(exclude)
    files: List[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel in excluded:
            continue
        files.append(rel)
    return files


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _normalize_checksum(value: str | None) -> str:
    if not value:
        return ""
    raw = value.strip()
    if raw.startswith("sha256:"):
        return raw.split(":", 1)[1]
    return raw
