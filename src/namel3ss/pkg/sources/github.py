from __future__ import annotations

import io
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.pkg.types import SourceSpec


class GitHubFetcher:
    def __init__(self, downloader: Callable[[str], bytes] | None = None) -> None:
        self._downloader = downloader

    def fetch(self, source: SourceSpec, dest: Path) -> Path:
        if source.scheme != "github":
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unsupported source scheme '{source.scheme}'.",
                    why="Only github: sources are supported in v0.",
                    fix="Use a github:owner/repo@ref source.",
                    example="github:namel3ss-ai/inventory@v0.1.0",
                )
            )
        dest.mkdir(parents=True, exist_ok=True)
        archive_bytes = self._download_archive(source)
        return _unpack_archive(archive_bytes, dest)

    def _download_archive(self, source: SourceSpec) -> bytes:
        url = f"https://codeload.github.com/{source.owner}/{source.repo}/zip/{source.ref}"
        if self._downloader:
            return self._downloader(url)
        req = urllib.request.Request(url, headers={"User-Agent": "namel3ss-pkg"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except urllib.error.HTTPError as err:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"GitHub download failed for {source.as_string()}.",
                    why=f"HTTP {err.code} while fetching {url}.",
                    fix="Check the repository, ref, and network access.",
                    example=source.as_string(),
                )
            ) from err
        except urllib.error.URLError as err:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"GitHub download failed for {source.as_string()}.",
                    why=f"Network error while fetching {url}.",
                    fix="Check your network connection and try again.",
                    example="n3 pkg install",
                )
            ) from err


def _unpack_archive(archive_bytes: bytes, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as zipf:
        _safe_extract(zipf, dest)
    roots = [path for path in dest.iterdir() if path.is_dir()]
    if len(roots) == 1:
        return roots[0]
    return dest


def _safe_extract(zipf: zipfile.ZipFile, dest: Path) -> None:
    dest_root = dest.resolve()
    for member in zipf.infolist():
        target = dest / member.filename
        try:
            resolved = target.resolve()
        except FileNotFoundError:
            continue
        if not str(resolved).startswith(str(dest_root)):
            raise Namel3ssError(
                build_guidance_message(
                    what="Archive contains unsafe paths.",
                    why="Package archives cannot write outside the destination folder.",
                    fix="Use a trusted package archive.",
                    example="github:namel3ss-ai/inventory@v0.1.0",
                )
            )
        zipf.extract(member, dest)
