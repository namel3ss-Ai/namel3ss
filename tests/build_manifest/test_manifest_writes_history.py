from pathlib import Path

from namel3ss.runtime.build.explain.manifest import BuildManifest
from namel3ss.runtime.build.explain.store import write_history


def test_manifest_writes_history(tmp_path: Path) -> None:
    manifest = BuildManifest(
        api_version="build",
        build_id="abc123",
        created_at="2024-01-01T00:00:00+00:00",
        project_root=str(tmp_path),
        app_path=str(tmp_path / "app.ai"),
        inputs={"source_fingerprint": "deadbeef", "files": [], "config": {}},
        guarantees=[],
        constraints=[],
        capabilities={},
        components={},
        changes=None,
        notes=[],
    )
    path = write_history(tmp_path, manifest)
    assert path.exists()
