from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse


_CONTENT_TYPES = {
    ".css": "text/css",
    ".gif": "image/gif",
    ".html": "text/html",
    ".ico": "image/x-icon",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".js": "application/javascript",
    ".json": "application/json",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".txt": "text/plain",
}


def resolve_external_ui_file(ui_root: Path, request_path: str) -> tuple[Path | None, str | None]:
    parsed = urlparse(request_path)
    path_only = parsed.path or "/"
    rel = "index.html" if path_only in {"/", ""} else path_only.lstrip("/")
    root = ui_root.resolve()
    candidate = (root / rel).resolve()
    if not _is_within(candidate, root):
        return None, None
    if candidate.is_dir():
        candidate = (candidate / "index.html").resolve()
        if not _is_within(candidate, root):
            return None, None
    if not candidate.exists():
        return None, None
    return candidate, _content_type(candidate)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _content_type(path: Path) -> str:
    return _CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")


__all__ = ["resolve_external_ui_file"]
