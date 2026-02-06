from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import zipfile

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.governance.policy import check_policies_for_source
from namel3ss.lint.engine import lint_source
from namel3ss.marketplace.capabilities import record_installed_item
from namel3ss.quality import run_quality_checks
from namel3ss.marketplace.index_store import (
    INDEX_FILE,
    RATINGS_FILE,
    item_key,
    load_index_entries,
    load_ratings,
    ratings_aggregate,
    same_item,
    version_sort_value,
    write_index_entries,
    write_ratings,
)
from namel3ss.marketplace.manifest import MANIFEST_FILE, MarketplaceItemManifest, load_manifest, validate_manifest_files
from namel3ss.runtime.persistence_paths import resolve_persistence_root, resolve_project_root
from namel3ss.utils.simple_yaml import render_yaml


REGISTRY_ENV = "N3_MARKETPLACE_REGISTRY"
BUNDLES_DIR = "bundles"



def marketplace_registry_root(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    allow_create: bool = True,
    override: str | None = None,
) -> Path:
    target = override or os.getenv(REGISTRY_ENV)
    if target:
        root = Path(target).expanduser()
        root = root.resolve() if root.exists() else root
    else:
        base = resolve_persistence_root(project_root, app_path, allow_create=allow_create)
        if base is None:
            raise Namel3ssError(_registry_root_message())
        root = Path(base) / ".namel3ss" / "marketplace" / "registry"
    if allow_create:
        root.mkdir(parents=True, exist_ok=True)
    return root



def publish_item(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    item_path: str | Path,
    registry_override: str | None = None,
) -> dict[str, object]:
    manifest, item_root = load_manifest(item_path)
    missing_files = validate_manifest_files(manifest, item_root)
    if missing_files:
        raise Namel3ssError(_missing_files_message(missing_files))

    _lint_manifest_files(manifest, item_root)
    bundle_one = _build_bundle_bytes(manifest, item_root)
    bundle_two = _build_bundle_bytes(manifest, item_root)
    if bundle_one != bundle_two:
        raise Namel3ssError(_non_deterministic_bundle_message())

    digest = _sha256(bundle_one)
    registry_root = marketplace_registry_root(project_root, app_path, override=registry_override)
    bundle_rel = f"{BUNDLES_DIR}/{manifest.name}-{manifest.version}.n3market.zip"
    bundle_path = registry_root / bundle_rel
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_bytes(bundle_one)

    entries = load_index_entries(registry_root)
    entry = _entry_from_manifest(manifest, bundle_rel, digest)
    entries = [item for item in entries if not same_item(item, manifest.name, manifest.version)]
    entries.append(entry)
    write_index_entries(registry_root, entries)

    return {
        "ok": True,
        "name": manifest.name,
        "version": manifest.version,
        "status": entry["status"],
        "bundle": bundle_path.as_posix(),
        "digest": digest,
    }



def approve_item(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    name: str,
    version: str,
    registry_override: str | None = None,
) -> dict[str, object]:
    registry_root = marketplace_registry_root(project_root, app_path, override=registry_override)
    entries = load_index_entries(registry_root)
    updated = False
    for entry in entries:
        if same_item(entry, name, version):
            entry["status"] = "approved"
            updated = True
    if not updated:
        raise Namel3ssError(_missing_item_message(name, version))
    write_index_entries(registry_root, entries)
    return {"ok": True, "name": name, "version": version, "status": "approved"}



def search_items(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    query: str,
    include_pending: bool = False,
    registry_override: str | None = None,
) -> list[dict[str, object]]:
    registry_root = marketplace_registry_root(project_root, app_path, allow_create=False, override=registry_override)
    entries = load_index_entries(registry_root)
    text = query.strip().lower()
    results: list[dict[str, object]] = []
    for entry in entries:
        status = str(entry.get("status") or "pending_review")
        if not include_pending and status != "approved":
            continue
        if text:
            haystack = " ".join(
                [
                    str(entry.get("name") or ""),
                    str(entry.get("description") or ""),
                    str(entry.get("type") or ""),
                ]
            ).lower()
            if text not in haystack:
                continue
        results.append(dict(entry))
    results.sort(key=lambda item: (str(item.get("name")), version_sort_value(str(item.get("version") or "0"))))
    return results



def install_item(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    name: str,
    version: str | None = None,
    include_pending: bool = False,
    registry_override: str | None = None,
) -> dict[str, object]:
    registry_root = marketplace_registry_root(project_root, app_path, allow_create=False, override=registry_override)
    entries = search_items(
        project_root=project_root,
        app_path=app_path,
        query=name,
        include_pending=include_pending,
        registry_override=registry_override,
    )
    candidates = [item for item in entries if str(item.get("name")) == name]
    if version:
        candidates = [item for item in candidates if str(item.get("version")) == version]
    if not candidates:
        raise Namel3ssError(_missing_item_message(name, version or "latest"))
    chosen = sorted(candidates, key=lambda item: version_sort_value(str(item.get("version") or "0")), reverse=True)[0]

    bundle_rel = str(chosen.get("bundle") or "")
    bundle_path = registry_root / bundle_rel
    if not bundle_path.exists():
        raise Namel3ssError(_missing_bundle_message(bundle_path))

    destination_root = _install_root(project_root, app_path)
    installed_files = _extract_bundle(bundle_path, destination_root)
    capabilities_path = record_installed_item(
        destination_root,
        name=str(chosen.get("name") or ""),
        version=str(chosen.get("version") or ""),
        item_type=str(chosen.get("type") or ""),
        files=[path.relative_to(destination_root).as_posix() for path in installed_files],
    )
    return {
        "ok": True,
        "name": chosen.get("name"),
        "version": chosen.get("version"),
        "capabilities_path": capabilities_path.as_posix(),
        "installed_files": [item.as_posix() for item in installed_files],
    }



def rate_item(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    name: str,
    version: str,
    rating: int,
    comment: str | None,
    registry_override: str | None = None,
) -> dict[str, object]:
    if rating < 1 or rating > 5:
        raise Namel3ssError(_invalid_rating_message())
    registry_root = marketplace_registry_root(project_root, app_path, override=registry_override)
    entries = load_index_entries(registry_root)
    if not any(same_item(entry, name, version) for entry in entries):
        raise Namel3ssError(_missing_item_message(name, version))

    ratings = load_ratings(registry_root)
    ratings.append(
        {
            "name": name,
            "version": version,
            "rating": int(rating),
            "comment": (comment or "").strip(),
        }
    )
    write_ratings(registry_root, ratings)

    aggregates = ratings_aggregate(ratings)
    for entry in entries:
        key = item_key(str(entry.get("name") or ""), str(entry.get("version") or ""))
        aggregate = aggregates.get(key)
        if aggregate:
            entry["rating_count"] = aggregate["count"]
            entry["rating_avg"] = aggregate["avg"]
    write_index_entries(registry_root, entries)
    return {"ok": True, "name": name, "version": version, "rating": rating}



def item_comments(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    name: str,
    version: str,
    registry_override: str | None = None,
) -> list[dict[str, object]]:
    registry_root = marketplace_registry_root(project_root, app_path, allow_create=False, override=registry_override)
    ratings = load_ratings(registry_root)
    comments = [
        {
            "rating": int(item.get("rating") or 0),
            "comment": str(item.get("comment") or ""),
        }
        for item in ratings
        if str(item.get("name") or "") == name and str(item.get("version") or "") == version and str(item.get("comment") or "").strip()
    ]
    comments.sort(key=lambda item: (int(item.get("rating") or 0), str(item.get("comment") or "")))
    return comments



def _build_bundle_bytes(manifest: MarketplaceItemManifest, item_root: Path) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        _write_zip_entry(archive, MANIFEST_FILE, render_yaml(manifest.to_dict()).encode("utf-8"))
        for relative in manifest.files:
            full_path = (item_root / relative).resolve()
            _write_zip_entry(archive, relative, full_path.read_bytes())
    return buffer.getvalue()



def _write_zip_entry(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name)
    info.date_time = (2000, 1, 1, 0, 0, 0)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, data)



def _lint_manifest_files(manifest: MarketplaceItemManifest, item_root: Path) -> None:
    for relative in manifest.files:
        path = (item_root / relative).resolve()
        if path.suffix != ".ai":
            continue
        source = path.read_text(encoding="utf-8")
        findings = lint_source(source)
        blocking = [item for item in findings if str(getattr(item, "severity", "warning")) == "error"]
        if blocking:
            raise Namel3ssError(_lint_failed_message(relative, blocking[0].message))
        quality_source = _quality_source_for_item(source)
        quality = run_quality_checks(quality_source, project_root=item_root, app_path=path)
        issues = quality.get("issues")
        if isinstance(issues, list) and issues:
            first = issues[0] if isinstance(issues[0], dict) else {}
            detail = str(first.get("issue") or "quality gate failed")
            raise Namel3ssError(_quality_failed_message(relative, detail))
        policy_violations = check_policies_for_source(
            project_root=item_root,
            app_path=path,
            source=source,
            source_name=relative,
        )
        if policy_violations:
            first_policy = policy_violations[0]
            detail = str(first_policy.get("description") or "policy violation")
            raise Namel3ssError(_quality_failed_message(relative, detail))


def _quality_source_for_item(source: str) -> str:
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("spec "):
            return source
        break
    return f'spec is "1.0"\n\n{source}'



def _entry_from_manifest(manifest: MarketplaceItemManifest, bundle_rel: str, digest: str) -> dict[str, object]:
    return {
        "name": manifest.name,
        "version": manifest.version,
        "type": manifest.item_type,
        "description": manifest.description,
        "author": manifest.author,
        "license": manifest.license,
        "files": list(manifest.files),
        "dependencies": list(manifest.dependencies),
        "bundle": bundle_rel,
        "digest": digest,
        "status": "pending_review",
        "rating_count": 0,
        "rating_avg": 0.0,
    }



def _extract_bundle(bundle_path: Path, destination_root: Path) -> list[Path]:
    installed: list[Path] = []
    with zipfile.ZipFile(bundle_path, "r") as archive:
        names = archive.namelist()
        if MANIFEST_FILE not in names:
            raise Namel3ssError(_invalid_bundle_message(bundle_path))
        manifest_bytes = archive.read(MANIFEST_FILE)
        manifest, _ = load_manifest_from_bytes(manifest_bytes)
        for relative in manifest.files:
            if relative not in names:
                raise Namel3ssError(_invalid_bundle_message(bundle_path))
            target = (destination_root / relative).resolve()
            if not _inside(destination_root.resolve(), target):
                raise Namel3ssError(_invalid_bundle_message(bundle_path))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(relative))
            installed.append(target)
    return sorted(installed, key=lambda path: path.as_posix())



def load_manifest_from_bytes(manifest_bytes: bytes) -> tuple[MarketplaceItemManifest, Path]:
    text = manifest_bytes.decode("utf-8")
    with TemporaryDirectory(prefix="n3-marketplace-") as tmp:
        temp_path = Path(tmp) / MANIFEST_FILE
        temp_path.write_text(text, encoding="utf-8")
        return load_manifest(temp_path)



def _install_root(project_root: str | Path | None, app_path: str | Path | None) -> Path:
    app_root = resolve_project_root(project_root, app_path)
    if app_root is None:
        raise Namel3ssError(_registry_root_message())
    app_root.mkdir(parents=True, exist_ok=True)
    return app_root



def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()



def _inside(root: Path, target: Path) -> bool:
    try:
        target.relative_to(root)
    except ValueError:
        return False
    return True



def _registry_root_message() -> str:
    return build_guidance_message(
        what="Marketplace registry path could not be resolved.",
        why="The project root is missing.",
        fix="Run the command from a project with app.ai.",
        example="n3 marketplace search flow",
    )



def _missing_files_message(missing: list[str]) -> str:
    return build_guidance_message(
        what="Marketplace manifest references missing files.",
        why=", ".join(missing),
        fix="Update manifest/capability files list or add the missing files.",
        example="files:\n  - app.ai",
    )



def _lint_failed_message(path: str, detail: str) -> str:
    return build_guidance_message(
        what="Marketplace item lint failed.",
        why=f"{path}: {detail}",
        fix="Fix lint errors before publishing.",
        example="n3 lint app.ai",
    )



def _quality_failed_message(path: str, detail: str) -> str:
    return build_guidance_message(
        what="Marketplace item quality gate failed.",
        why=f"{path}: {detail}",
        fix="Fix quality issues before publishing.",
        example="n3 quality check app.ai",
    )


def _non_deterministic_bundle_message() -> str:
    return build_guidance_message(
        what="Marketplace packaging is not deterministic.",
        why="The package bytes changed between two consecutive builds.",
        fix="Remove dynamic fields such as timestamps from package inputs.",
        example="n3 marketplace publish ./item",
    )



def _missing_item_message(name: str, version: str) -> str:
    return build_guidance_message(
        what=f'Marketplace item "{name}" was not found.',
        why=f"Version {version} is not in the registry index.",
        fix="Search available items and verify the version.",
        example=f"n3 marketplace search {name}",
    )



def _missing_bundle_message(path: Path) -> str:
    return build_guidance_message(
        what="Marketplace bundle is missing.",
        why=f"Expected {path.as_posix()} to exist.",
        fix="Republish the item.",
        example="n3 marketplace publish ./item",
    )



def _invalid_bundle_message(path: Path) -> str:
    return build_guidance_message(
        what="Marketplace bundle is invalid.",
        why=f"{path.as_posix()} is missing required files.",
        fix="Republish the item and retry installation.",
        example="n3 marketplace install demo.item",
    )



def _invalid_rating_message() -> str:
    return build_guidance_message(
        what="Marketplace rating is invalid.",
        why="Rating must be an integer from 1 to 5.",
        fix="Use a value in that range.",
        example="n3 marketplace rate demo.item 0.1.0 5",
    )


__all__ = [
    "BUNDLES_DIR",
    "INDEX_FILE",
    "RATINGS_FILE",
    "approve_item",
    "install_item",
    "item_comments",
    "marketplace_registry_root",
    "publish_item",
    "rate_item",
    "search_items",
]
