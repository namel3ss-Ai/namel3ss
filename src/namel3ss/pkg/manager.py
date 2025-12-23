from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.pkg.install import FetchSession
from namel3ss.pkg.manifest import load_manifest
from namel3ss.pkg.metadata import load_metadata
from namel3ss.pkg.resolver import ResolutionResult, resolve_dependencies
from namel3ss.pkg.types import Manifest, SourceSpec


def resolve_project(root: Path, *, session: FetchSession | None = None) -> tuple[Manifest, ResolutionResult, FetchSession]:
    manifest = load_manifest(root)
    fetch_session = session or FetchSession()

    def fetch_metadata(source: SourceSpec):
        root_path = fetch_session.fetch(source)
        metadata = load_metadata(root_path)
        if metadata.source.as_string() != source.as_string():
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Package source mismatch for '{metadata.name}'.",
                    why=f"Metadata declares {metadata.source.as_string()}, expected {source.as_string()}.",
                    fix="Use the correct source or update the package metadata.",
                    example=source.as_string(),
                )
            )
        return metadata

    resolution = resolve_dependencies(manifest.dependencies.values(), fetch_metadata)
    return manifest, resolution, fetch_session
