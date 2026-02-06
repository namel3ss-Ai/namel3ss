from __future__ import annotations

import os
import re
import shutil
import stat
import sys
import time
from pathlib import Path
from typing import Callable
from urllib.parse import unquote, urlparse


_WIN_RETRY_ERRORS = {5, 32}
_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:$")
_WINDOWS_DRIVE_PATH_RE = re.compile(r"^/[A-Za-z]:([/\\\\].*)?$")


def remove_tree(path: Path, *, retries: int = 3, delay: float = 0.05) -> None:
    """Remove a directory tree, retrying on transient Windows locks."""
    if not path.exists():
        return
    if not _is_windows():
        shutil.rmtree(path)
        return

    def _onerror(func: Callable[[str], None], target: str, exc_info) -> None:
        del exc_info
        try:
            os.chmod(target, stat.S_IWRITE)
        except OSError:
            pass
        func(target)

    attempt = 0
    while True:
        try:
            shutil.rmtree(path, onerror=_onerror)
            return
        except OSError as err:
            winerror = getattr(err, "winerror", None)
            if winerror not in _WIN_RETRY_ERRORS or attempt >= retries:
                raise
            attempt += 1
            time.sleep(delay)


def _is_windows() -> bool:
    return sys.platform.startswith("win")


def resolve_file_uri(value: str | Path) -> Path:
    """
    Resolve local filesystem inputs in either plain path or file:// URI form.

    Supported forms:
    - /tmp/registry.json
    - C:\\Users\\name\\registry.json
    - file:///tmp/registry.json
    - file:///C:/Users/name/registry.json
    - file://C:/Users/name/registry.json
    """
    if isinstance(value, Path):
        return value
    text = str(value or "").strip()
    if not text:
        raise ValueError("path is required")
    parsed = urlparse(text)
    scheme = (parsed.scheme or "").lower()
    if scheme not in {"", "file"}:
        raise ValueError(f"unsupported URI scheme '{parsed.scheme}'")
    if scheme == "":
        return Path(text)

    netloc = unquote(parsed.netloc or "")
    raw_path = unquote(parsed.path or "")
    if parsed.params or parsed.query or parsed.fragment:
        raise ValueError("file URI must not include params, query, or fragment")
    if netloc in {".", ".."}:
        return Path(f"{netloc}{raw_path}")
    if netloc and netloc.lower() != "localhost":
        if _WINDOWS_DRIVE_RE.match(netloc):
            return Path(f"{netloc}{raw_path}")
        return Path(f"//{netloc}{raw_path}")
    if _WINDOWS_DRIVE_PATH_RE.match(raw_path):
        return Path(raw_path[1:])
    if raw_path:
        return Path(raw_path)
    raise ValueError("file URI path is empty")


__all__ = ["remove_tree", "resolve_file_uri"]
