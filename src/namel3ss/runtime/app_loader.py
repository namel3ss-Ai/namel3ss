from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError


@dataclass(frozen=True)
class LoadedAppArchive:
    path: Path
    checksum: str
    files: dict[str, bytes]
    descriptor: dict[str, object]
    compiled_ir: dict[str, object]
    ui_manifest: dict[str, object]
    permissions: dict[str, bool]
    ui_state_schema: dict[str, object]
    runtime_config: dict[str, object]


REQUIRED_ARCHIVE_FILES = (
    "app_descriptor.json",
    "compiled_ir.json",
    "permissions.json",
    "runtime_config.json",
    "static_assets.json",
    "ui_manifest.json",
    "ui_state_schema.json",
)


def load_app_archive(path: str | Path) -> LoadedAppArchive:
    archive_path = Path(path)
    if archive_path.suffix != ".n3a":
        raise Namel3ssError("This file is not a namel3ss app.")
    if not archive_path.exists() or not archive_path.is_file():
        raise Namel3ssError("This file is not a namel3ss app.")

    checksum = _sha256(archive_path)
    try:
        with zipfile.ZipFile(archive_path, mode="r") as archive:
            names = sorted(name for name in archive.namelist() if not name.endswith("/"))
            files = {name: archive.read(name) for name in names}
    except zipfile.BadZipFile as err:
        raise Namel3ssError("This file is not a namel3ss app.") from err

    missing = [name for name in REQUIRED_ARCHIVE_FILES if name not in files]
    if missing:
        raise Namel3ssError("This file is not a namel3ss app.")

    descriptor = _read_json_dict(files, "app_descriptor.json")
    compiled_ir = _read_json_dict(files, "compiled_ir.json")
    ui_manifest = _read_json_dict(files, "ui_manifest.json")
    permissions = _read_json_bool_map(files, "permissions.json")
    ui_state_schema = _read_json_dict(files, "ui_state_schema.json")
    runtime_config = _read_json_dict(files, "runtime_config.json")

    return LoadedAppArchive(
        path=archive_path.resolve(),
        checksum=checksum,
        files=files,
        descriptor=descriptor,
        compiled_ir=compiled_ir,
        ui_manifest=ui_manifest,
        permissions=permissions,
        ui_state_schema=ui_state_schema,
        runtime_config=runtime_config,
    )


def _read_json_dict(files: dict[str, bytes], name: str) -> dict[str, object]:
    payload = _read_json(files, name)
    if not isinstance(payload, dict):
        raise Namel3ssError("This file is not a namel3ss app.")
    return payload


def _read_json_bool_map(files: dict[str, bytes], name: str) -> dict[str, bool]:
    payload = _read_json(files, name)
    if not isinstance(payload, dict):
        raise Namel3ssError("This file is not a namel3ss app.")
    return {str(key): bool(value) for key, value in payload.items()}


def _read_json(files: dict[str, bytes], name: str) -> object:
    raw = files.get(name)
    if raw is None:
        raise Namel3ssError("This file is not a namel3ss app.")
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise Namel3ssError("This file is not a namel3ss app.") from err


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


__all__ = ["LoadedAppArchive", "REQUIRED_ARCHIVE_FILES", "load_app_archive"]
