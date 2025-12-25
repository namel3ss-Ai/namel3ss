from __future__ import annotations

import hashlib
import zipfile
from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.layout import PACK_SOURCE_META, PACK_VERIFICATION
from namel3ss.runtime.packs.manifest import parse_pack_manifest


EXCLUDE_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".namel3ss"}
EXCLUDE_FILES = {PACK_VERIFICATION, PACK_SOURCE_META, ".DS_Store"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}
TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".toml", ".json", ".py", ".ai", ".txt"}


@dataclass(frozen=True)
class PackBundleResult:
    pack_id: str
    version: str
    bundle_path: Path
    file_count: int
    digest: str


def bundle_pack(pack_dir: Path, *, out_dir: Path) -> PackBundleResult:
    manifest = parse_pack_manifest(pack_dir / "pack.yaml")
    out_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = out_dir / f"{manifest.pack_id}-{manifest.version}.n3pack.zip"
    file_paths = _gather_files(pack_dir)
    _write_bundle(bundle_path, pack_dir, file_paths)
    digest = _sha256(bundle_path)
    return PackBundleResult(
        pack_id=manifest.pack_id,
        version=manifest.version,
        bundle_path=bundle_path,
        file_count=len(file_paths),
        digest=digest,
    )


def _gather_files(pack_dir: Path) -> list[Path]:
    if not pack_dir.exists():
        raise Namel3ssError(_missing_pack_message(pack_dir))
    files: list[Path] = []
    for path in pack_dir.rglob("*"):
        if path.is_dir():
            continue
        rel = path.relative_to(pack_dir)
        if _excluded(rel):
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(pack_dir).as_posix())


def _excluded(rel: Path) -> bool:
    if any(part in EXCLUDE_DIRS for part in rel.parts):
        return True
    if rel.name in EXCLUDE_FILES:
        return True
    if rel.suffix in EXCLUDE_SUFFIXES:
        return True
    return False


def _write_bundle(bundle_path: Path, pack_dir: Path, files: list[Path]) -> None:
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            rel = path.relative_to(pack_dir).as_posix()
            info = zipfile.ZipInfo(rel)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            data = _read_payload(path)
            archive.writestr(info, data)


def _read_payload(path: Path) -> bytes:
    if path.suffix in TEXT_SUFFIXES:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            return path.read_bytes()
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        return normalized.encode("utf-8")
    return path.read_bytes()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return f"sha256:{digest.hexdigest()}"


def _missing_pack_message(path: Path) -> str:
    return build_guidance_message(
        what="Pack directory was not found.",
        why=f"Expected {path.as_posix()} to exist.",
        fix="Pass a valid pack directory.",
        example="n3 packs bundle ./my_pack",
    )


__all__ = ["PackBundleResult", "bundle_pack"]
