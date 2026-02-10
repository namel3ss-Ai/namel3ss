from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import shutil
import zipfile

from namel3ss.determinism import canonical_json_dump
from namel3ss.errors.base import Namel3ssError

_SUPPORTED_CHANNELS: tuple[str, ...] = ("container", "filesystem", "npm", "pypi")


@dataclass(frozen=True)
class DeploymentRecord:
    channel: str
    artifact: str
    sha256: str
    size_bytes: int
    status: str

    def as_dict(self) -> dict[str, object]:
        return {
            "channel": self.channel,
            "artifact": self.artifact,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "status": self.status,
        }


@dataclass(frozen=True)
class DeploymentBundle:
    report_path: Path
    records: tuple[DeploymentRecord, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "report_path": self.report_path.as_posix(),
            "records": [record.as_dict() for record in self.records],
        }


def deploy_bundle_archive(
    archive_path: str | Path,
    *,
    out_dir: str | Path | None = None,
    channels: tuple[str, ...] = ("filesystem",),
) -> DeploymentBundle:
    archive = _resolve_archive_path(archive_path)
    output_root = _resolve_output_root(archive, out_dir)
    metadata = _read_package_manifest_from_archive(archive)
    channel_list = _normalize_channels(channels)

    records: list[DeploymentRecord] = []
    for channel in channel_list:
        target_dir = (output_root / channel).resolve()
        target_dir.mkdir(parents=True, exist_ok=True)
        target_archive = target_dir / archive.name
        shutil.copyfile(archive, target_archive)
        digest = _sha256(target_archive)
        records.append(
            DeploymentRecord(
                channel=channel,
                artifact=target_archive.as_posix(),
                sha256=digest,
                size_bytes=target_archive.stat().st_size,
                status="ready",
            )
        )

    report_payload = {
        "schema_version": "1",
        "source_archive": archive.as_posix(),
        "version": metadata.get("version", "0.0.0-dev"),
        "target": metadata.get("target", "service"),
        "records": [record.as_dict() for record in sorted(records, key=lambda item: item.channel)],
    }
    report_path = output_root / "deploy_report.json"
    canonical_json_dump(report_path, report_payload, pretty=True, drop_run_keys=False)
    return DeploymentBundle(report_path=report_path, records=tuple(sorted(records, key=lambda item: item.channel)))


def _resolve_archive_path(value: str | Path) -> Path:
    archive = Path(value).expanduser().resolve()
    if not archive.exists() or not archive.is_file():
        raise Namel3ssError(f"Deploy input archive was not found: {archive.as_posix()}")
    if archive.suffix.lower() != ".zip":
        raise Namel3ssError("Deploy input must be a .zip archive.")
    return archive


def _resolve_output_root(archive_path: Path, out_dir: str | Path | None) -> Path:
    if out_dir is None:
        target = archive_path.parent / "deploy"
    else:
        raw = Path(out_dir)
        target = raw if raw.is_absolute() else (Path.cwd() / raw)
    target.mkdir(parents=True, exist_ok=True)
    return target.resolve()


def _normalize_channels(channels: tuple[str, ...]) -> tuple[str, ...]:
    normalized = sorted({str(channel).strip().lower() for channel in channels if str(channel).strip()})
    if not normalized:
        raise Namel3ssError("Deploy requires at least one channel.")
    for channel in normalized:
        if channel not in _SUPPORTED_CHANNELS:
            allowed = ", ".join(_SUPPORTED_CHANNELS)
            raise Namel3ssError(f"Deploy channel '{channel}' is unsupported. Allowed: {allowed}.")
    return tuple(normalized)


def _read_package_manifest_from_archive(path: Path) -> dict[str, object]:
    with zipfile.ZipFile(path, mode="r") as archive:
        names = sorted(name for name in archive.namelist() if not name.endswith("/"))
        if "package_manifest.json" not in names:
            return {}
        raw = archive.read("package_manifest.json")
    import json

    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        return {}
    return {str(key): payload[key] for key in sorted(payload.keys(), key=lambda item: str(item))}


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


__all__ = [
    "DeploymentBundle",
    "DeploymentRecord",
    "deploy_bundle_archive",
]
