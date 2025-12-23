from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from namel3ss.pkg.sources.github import GitHubFetcher
from namel3ss.pkg.types import SourceSpec


def _make_zip_bytes(root: Path, prefix: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            zipf.writestr(f"{prefix}/{rel}", path.read_bytes())
    return buffer.getvalue()


def test_github_fetcher_unpack(tmp_path: Path) -> None:
    package_root = tmp_path / "source"
    package_root.mkdir()
    (package_root / "capsule.ai").write_text('capsule "demo":\n  exports:\n    flow "run"\n', encoding="utf-8")
    (package_root / "namel3ss.package.json").write_text(
        json.dumps(
            {
                "name": "demo",
                "version": "0.1.0",
                "source": "github:owner/demo@v0.1.0",
                "license": "MIT",
                "checksums": "checksums.json",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (package_root / "checksums.json").write_text('{"files":{}}', encoding="utf-8")

    archive_bytes = _make_zip_bytes(package_root, "owner-demo-v0.1.0")
    fetcher = GitHubFetcher(downloader=lambda url: archive_bytes)
    dest = tmp_path / "out"
    root = fetcher.fetch(SourceSpec(scheme="github", owner="owner", repo="demo", ref="v0.1.0"), dest)
    assert (root / "capsule.ai").exists()
