from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
from typing import Mapping

from namel3ss.cli.app_loader import load_program
from namel3ss.config.loader import load_config
from namel3ss.determinism import canonical_json_dump, canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.performance.profiler import BuildProfile, profile_app_build
from namel3ss.tools.app_archive import write_archive
from namel3ss.validation_entrypoint import build_static_manifest

_ALLOWED_TARGETS: tuple[str, ...] = ("local", "service", "edge")
_DISTRIBUTION_CHANNELS: tuple[str, ...] = ("container", "npm", "pypi")
_JSON_CACHE: dict[tuple[str, str], object] = {}


@dataclass(frozen=True)
class BuildArtifact:
    kind: str
    path: str
    sha256: str
    size_bytes: int

    def as_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "path": self.path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }


@dataclass(frozen=True)
class BuildBundle:
    root: Path
    archive: Path
    package_manifest: Path
    artifacts: tuple[BuildArtifact, ...]
    profile: BuildProfile | None

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "root": self.root.as_posix(),
            "archive": self.archive.as_posix(),
            "package_manifest": self.package_manifest.as_posix(),
            "artifacts": [artifact.as_dict() for artifact in self.artifacts],
        }
        if self.profile is not None:
            payload["performance"] = self.profile.as_dict()
        return payload


def build_deployable_bundle(
    app_path: str | Path,
    *,
    out_dir: str | Path | None = None,
    target: str = "service",
    include_profile: bool = False,
    profile_iterations: int = 1,
) -> BuildBundle:
    app_file = _resolve_app_path(app_path)
    normalized_target = _normalize_target(target)
    project_root = app_file.parent
    output_root = _resolve_output_root(project_root, out_dir)
    bundle_root = (output_root / f"{app_file.stem}_{normalized_target}").resolve()
    archive_path = (output_root / f"{app_file.stem}_{normalized_target}.n3bundle.zip").resolve()
    _prepare_bundle_root(bundle_root)

    config = load_config(app_path=app_file)
    program, _sources = load_program(app_file.as_posix())
    manifest = build_static_manifest(program, config=config, state={}, store=None, warnings=[])
    manifest_json = canonical_json_dumps(manifest, pretty=True, drop_run_keys=False)

    written_artifacts: list[BuildArtifact] = []
    manifest_path = bundle_root / "manifest.json"
    _write_text(manifest_path, manifest_json)
    written_artifacts.append(_build_artifact("manifest", manifest_path, base=bundle_root))

    written_artifacts.extend(_copy_asset_tree(project_root, bundle_root))
    capabilities = tuple(sorted(str(item) for item in getattr(program, "capabilities", ()) or ()))
    profile = profile_app_build(app_file, iterations=profile_iterations, enabled=include_profile)
    if include_profile:
        profile_path = bundle_root / "performance_profile.json"
        canonical_json_dump(profile_path, profile.as_dict(), pretty=True, drop_run_keys=False)
        written_artifacts.append(_build_artifact("performance", profile_path, base=bundle_root))
    else:
        profile = None

    package_manifest_payload = _build_package_manifest_payload(
        app_file=app_file,
        target=normalized_target,
        capabilities=capabilities,
        artifacts=written_artifacts,
    )
    package_manifest_path = bundle_root / "package_manifest.json"
    canonical_json_dump(package_manifest_path, package_manifest_payload, pretty=True, drop_run_keys=False)
    written_artifacts.append(_build_artifact("metadata", package_manifest_path, base=bundle_root))

    _write_bundle_archive(bundle_root, archive_path)
    written_artifacts.append(_build_artifact("archive", archive_path, base=output_root))
    artifacts = tuple(sorted(written_artifacts, key=lambda item: (item.kind, item.path)))
    return BuildBundle(
        root=bundle_root,
        archive=archive_path,
        package_manifest=package_manifest_path,
        artifacts=artifacts,
        profile=profile,
    )


def _resolve_app_path(value: str | Path) -> Path:
    app_file = Path(value).expanduser().resolve()
    if app_file.suffix != ".ai":
        raise Namel3ssError("Build input must be an .ai file.")
    if not app_file.exists() or not app_file.is_file():
        raise Namel3ssError(f"Build input was not found: {app_file.as_posix()}")
    return app_file


def _normalize_target(value: str) -> str:
    target = str(value or "").strip().lower()
    if target not in _ALLOWED_TARGETS:
        allowed = ", ".join(_ALLOWED_TARGETS)
        raise Namel3ssError(f"Build target must be one of: {allowed}.")
    return target


def _resolve_output_root(project_root: Path, out_dir: str | Path | None) -> Path:
    if out_dir is None:
        target = project_root / "dist"
    else:
        raw_path = Path(out_dir)
        target = raw_path if raw_path.is_absolute() else (project_root / raw_path)
    target.mkdir(parents=True, exist_ok=True)
    return target.resolve()


def _prepare_bundle_root(bundle_root: Path) -> None:
    if bundle_root.exists():
        shutil.rmtree(bundle_root)
    bundle_root.mkdir(parents=True, exist_ok=False)


def _copy_asset_tree(project_root: Path, bundle_root: Path) -> list[BuildArtifact]:
    artifacts: list[BuildArtifact] = []
    for folder in ("i18n", "plugins", "themes"):
        source_root = project_root / folder
        if not source_root.exists() or not source_root.is_dir():
            continue
        for source_path in sorted(path for path in source_root.rglob("*") if path.is_file()):
            rel = source_path.resolve().relative_to(project_root.resolve())
            _validate_asset_file(source_path, rel)
            destination = bundle_root / "assets" / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source_path.read_bytes())
            artifacts.append(_build_artifact("asset", destination, base=bundle_root))
    return artifacts


def _validate_asset_file(source_path: Path, relative_path: Path) -> None:
    normalized = relative_path.as_posix()
    if normalized.startswith("i18n/locales/") and source_path.suffix.lower() == ".json":
        _load_json_cached(source_path)
    if normalized.startswith("plugins/") and source_path.name in {"plugin.json", "manifest.json"}:
        _load_json_cached(source_path)


def _load_json_cached(path: Path) -> object:
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    key = (path.resolve().as_posix(), digest)
    if key in _JSON_CACHE:
        return _JSON_CACHE[key]
    try:
        data = json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError as err:
        raise Namel3ssError(
            f"Invalid JSON asset '{path.as_posix()}': {err.msg}",
            line=err.lineno,
            column=err.colno,
        ) from err
    _JSON_CACHE[key] = data
    return data


def _build_package_manifest_payload(
    *,
    app_file: Path,
    target: str,
    capabilities: tuple[str, ...],
    artifacts: list[BuildArtifact],
) -> dict[str, object]:
    return {
        "schema_version": "1",
        "app": app_file.name,
        "target": target,
        "version": _resolve_version(),
        "distribution_channels": list(_DISTRIBUTION_CHANNELS),
        "capabilities": list(capabilities),
        "artifacts": [item.as_dict() for item in sorted(artifacts, key=lambda entry: (entry.kind, entry.path))],
    }


def _resolve_version() -> str:
    try:
        value = importlib.metadata.version("namel3ss")
    except importlib.metadata.PackageNotFoundError:
        value = "0.0.0-dev"
    return str(value)


def _write_bundle_archive(bundle_root: Path, archive_path: Path) -> None:
    entries: dict[str, bytes] = {}
    for file_path in sorted(path for path in bundle_root.rglob("*") if path.is_file()):
        rel = file_path.resolve().relative_to(bundle_root.resolve()).as_posix()
        entries[rel] = file_path.read_bytes()
    write_archive(archive_path, entries)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _build_artifact(kind: str, path: Path, *, base: Path) -> BuildArtifact:
    payload = path.read_bytes()
    return BuildArtifact(
        kind=kind,
        path=path.resolve().relative_to(base.resolve()).as_posix(),
        sha256=hashlib.sha256(payload).hexdigest(),
        size_bytes=len(payload),
    )


def parse_package_manifest(path: str | Path) -> dict[str, object]:
    payload = _load_json_cached(Path(path).expanduser().resolve())
    if not isinstance(payload, Mapping):
        raise Namel3ssError("Package manifest must be a JSON object.")
    return {str(key): payload[key] for key in sorted(payload.keys(), key=lambda item: str(item))}


__all__ = [
    "BuildArtifact",
    "BuildBundle",
    "build_deployable_bundle",
    "parse_package_manifest",
]
