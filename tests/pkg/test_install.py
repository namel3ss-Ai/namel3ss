from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from namel3ss.pkg.install import FetchSession, install_from_resolution
from namel3ss.pkg.metadata import load_metadata
from namel3ss.pkg.resolver import ResolutionResult
from namel3ss.pkg.types import DependencySpec, SourceSpec


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _write_checksums(root: Path) -> None:
    files = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name == "checksums.json":
            continue
        rel = path.relative_to(root).as_posix()
        files[rel] = f"sha256:{_sha256(path)}"
    (root / "checksums.json").write_text(json.dumps({"files": files}, indent=2), encoding="utf-8")


class LocalFetcher:
    def __init__(self, mapping: dict[str, Path]) -> None:
        self.mapping = mapping

    def fetch(self, source: SourceSpec, dest: Path) -> Path:
        src_root = self.mapping[source.as_string()]
        target = dest / "pkg"
        shutil.copytree(src_root, target)
        return target


def test_install_from_resolution(tmp_path: Path) -> None:
    package_root = tmp_path / "package_src"
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
    _write_checksums(package_root)

    meta = load_metadata(package_root)
    resolution = ResolutionResult(packages={"demo": meta})
    source = SourceSpec(scheme="github", owner="owner", repo="demo", ref="v0.1.0")
    roots = [DependencySpec(name="demo", source=source)]

    session = FetchSession(fetcher=LocalFetcher({source.as_string(): package_root}))
    lockfile = install_from_resolution(tmp_path, roots, resolution, fetch_session=session)
    session.close()

    assert (tmp_path / "packages" / "demo" / "capsule.ai").exists()
    assert lockfile.packages[0].name == "demo"
