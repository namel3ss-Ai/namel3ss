from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path
from typing import Mapping


ARCHIVE_EXTENSION = ".n3a"
ARCHIVE_FORMAT = "n3a.v1"
_ARCHIVE_TIMESTAMP = (2000, 1, 1, 0, 0, 0)


class AppArchiveError(RuntimeError):
    pass


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def archive_sha256(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def build_archive_bytes(entries: Mapping[str, bytes | str]) -> bytes:
    normalized = _normalize_entries(entries)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(normalized.keys()):
            info = zipfile.ZipInfo(name)
            info.date_time = _ARCHIVE_TIMESTAMP
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, normalized[name])
    return buffer.getvalue()


def write_archive(path: Path, entries: Mapping[str, bytes | str]) -> str:
    data = build_archive_bytes(entries)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return sha256_bytes(data)


def read_archive(path: Path) -> dict[str, bytes]:
    target = Path(path)
    if not target.exists():
        raise AppArchiveError("This file is not a namel3ss app.")
    try:
        with zipfile.ZipFile(target, mode="r") as archive:
            names = sorted(name for name in archive.namelist() if not name.endswith("/"))
            result: dict[str, bytes] = {}
            for name in names:
                _validate_entry_name(name)
                result[name] = archive.read(name)
            return result
    except zipfile.BadZipFile as err:
        raise AppArchiveError("This file is not a namel3ss app.") from err


def _normalize_entries(entries: Mapping[str, bytes | str]) -> dict[str, bytes]:
    normalized: dict[str, bytes] = {}
    for raw_name, raw_payload in entries.items():
        name = str(raw_name)
        _validate_entry_name(name)
        if isinstance(raw_payload, bytes):
            payload = raw_payload
        elif isinstance(raw_payload, str):
            payload = raw_payload.encode("utf-8")
        else:
            raise AppArchiveError(f"Archive entry '{name}' is not valid text or bytes.")
        normalized[name] = payload
    return normalized


def _validate_entry_name(name: str) -> None:
    if not name:
        raise AppArchiveError("Archive entry names cannot be empty.")
    if name.startswith("/"):
        raise AppArchiveError("Archive entries cannot use absolute paths.")
    parts = name.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise AppArchiveError("Archive entries contain an invalid path.")


__all__ = [
    "AppArchiveError",
    "ARCHIVE_EXTENSION",
    "ARCHIVE_FORMAT",
    "archive_sha256",
    "build_archive_bytes",
    "read_archive",
    "sha256_bytes",
    "write_archive",
]
