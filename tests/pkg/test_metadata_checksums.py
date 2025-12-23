from __future__ import annotations

import hashlib
import json
from pathlib import Path

from namel3ss.pkg.checksums import verify_checksums
from namel3ss.pkg.metadata import load_metadata


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _write_checksums(root: Path, checksums_name: str) -> None:
    files = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name == checksums_name:
            continue
        rel = path.relative_to(root).as_posix()
        files[rel] = f"sha256:{_sha256(path)}"
    payload = {"files": files}
    (root / checksums_name).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_metadata_and_checksums_load(tmp_path: Path) -> None:
    package_root = tmp_path / "pkg"
    package_root.mkdir()
    (package_root / "capsule.ai").write_text('capsule "demo":\n  exports:\n    flow "run"\n', encoding="utf-8")
    (package_root / "logic.ai").write_text('flow "run":\n  return "ok"\n', encoding="utf-8")
    (package_root / "LICENSE").write_text("MIT", encoding="utf-8")
    metadata = {
        "name": "demo",
        "version": "0.1.0",
        "source": "github:owner/demo@v0.1.0",
        "license_file": "LICENSE",
        "checksums": "checksums.json",
    }
    (package_root / "namel3ss.package.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    _write_checksums(package_root, "checksums.json")

    loaded = load_metadata(package_root)
    assert loaded.name == "demo"
    entries = verify_checksums(package_root, package_root / "checksums.json")
    paths = {entry.path for entry in entries}
    assert "capsule.ai" in paths
    assert "namel3ss.package.json" in paths
