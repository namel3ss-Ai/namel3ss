from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlparse


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


def resolve_builtin_icon_file(request_path: str) -> tuple[Path | None, str | None]:
    parsed = urlparse(request_path)
    path_only = parsed.path or "/"
    prefix = "/icons/"
    if not path_only.startswith(prefix):
        return None, None
    rel = unquote(path_only[len(prefix) :].strip("/"))
    if not rel:
        return None, None
    requested = Path(rel)
    if requested.suffix and requested.suffix.lower() != ".svg":
        return None, None
    icon_name = requested.stem
    if not icon_name:
        return None, None
    from namel3ss.icons.registry import icon_registry, normalize_icon_name

    candidate = icon_registry().get(normalize_icon_name(icon_name))
    if candidate is None or not candidate.exists():
        return None, None
    return candidate, "image/svg+xml"


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _content_type(path: Path) -> str:
    return _CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")


__all__ = ["resolve_builtin_icon_file", "resolve_external_ui_file"]
