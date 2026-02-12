from __future__ import annotations

import json
from pathlib import Path

import pytest

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.studio.renderer_registry.manifest_schema import (
    RENDERER_MANIFEST_SCHEMA_VERSION,
    RendererManifest,
    RendererManifestEntry,
)
from namel3ss.studio.startup.startup_validation import (
    reset_renderer_registry_startup_cache,
    validate_renderer_registry_startup,
)
from tools.build_renderer_manifest import build_manifest


MANIFEST_PATH = Path("src/namel3ss/studio/web/renderer_manifest.json")


def test_renderer_manifest_is_sorted_and_deterministic() -> None:
    on_disk = MANIFEST_PATH.read_text(encoding="utf-8")
    manifest = json.loads(on_disk)
    assert manifest["schema_version"] == RENDERER_MANIFEST_SCHEMA_VERSION

    renderer_ids = [entry["renderer_id"] for entry in manifest["renderers"]]
    assert renderer_ids == sorted(renderer_ids)
    assert "audit_viewer" in renderer_ids
    assert "state_inspector" in renderer_ids

    for entry in manifest["renderers"]:
        exports = entry.get("exports", [])
        assert exports == sorted(exports)

    generated = canonical_json_dumps(build_manifest(), pretty=True, drop_run_keys=False)
    assert generated == on_disk


def test_startup_validation_accepts_current_manifest() -> None:
    reset_renderer_registry_startup_cache()
    renderer_ids = validate_renderer_registry_startup()
    assert "audit_viewer" in renderer_ids
    assert "state_inspector" in renderer_ids


def test_startup_validation_raises_missing_required_error_code(monkeypatch) -> None:
    from namel3ss.studio.renderer_registry import registry_validator

    bad_manifest = RendererManifest(
        schema_version=RENDERER_MANIFEST_SCHEMA_VERSION,
        renderers=(
            RendererManifestEntry(
                renderer_id="audit_viewer",
                entrypoint="ui_renderer_audit_viewer.js",
                entrypoint_hash="sha256:1",
                version="1",
                integrity_hash="sha256:1",
                exports=("renderAuditViewerElement",),
            ),
        ),
    )
    monkeypatch.setattr(registry_validator, "load_renderer_manifest", lambda path=None: bad_manifest)
    reset_renderer_registry_startup_cache()
    with pytest.raises(Namel3ssError) as excinfo:
        validate_renderer_registry_startup()
    assert "N3E_RENDERER_REQUIRED_MISSING" in str(excinfo.value)
