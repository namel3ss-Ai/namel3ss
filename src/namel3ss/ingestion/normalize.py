from __future__ import annotations

import re

from namel3ss.observability.scrub import scrub_text
from namel3ss.secrets import redact_text


_HYPHEN_BREAK_RE = re.compile(r"(?<=\\w)-\\n(?=\\w)")
_MULTI_BLANK_RE = re.compile(r"\\n{3,}")
_INLINE_POSIX_PATH = re.compile(r"(?<![A-Za-z0-9])/(?:[^\\s]+)")
_SAFE_PREFIXES = ("/api/", "/health", "/version", "/ui", "/docs/")


def normalize_text(text: str) -> str:
    if not text:
        return ""
    native = _native_normalize_text(text)
    if native is not None:
        return native
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = _HYPHEN_BREAK_RE.sub("", cleaned)
    cleaned = _suppress_headers_footers(cleaned)
    if "\f" in cleaned:
        pages = cleaned.split("\f")
        normalized_pages = []
        for page in pages:
            lines = [" ".join(line.split()) for line in page.splitlines()]
            normalized = "\n".join(lines)
            normalized = _MULTI_BLANK_RE.sub("\n\n", normalized)
            normalized_pages.append(normalized.strip(" \t\r\n"))
        return "\f".join(normalized_pages).strip(" \t\r\n")
    lines = [" ".join(line.split()) for line in cleaned.splitlines()]
    cleaned = "\n".join(lines)
    cleaned = _MULTI_BLANK_RE.sub("\n\n", cleaned)
    cleaned = cleaned.strip(" \t\r\n")
    return cleaned


def sanitize_text(
    text: str,
    *,
    project_root: str | None = None,
    app_path: str | None = None,
    secret_values: list[str] | None = None,
) -> str:
    cleaned = redact_text(text or "", secret_values or [])
    cleaned = scrub_text(cleaned, project_root=project_root, app_path=app_path)
    return _scrub_inline_paths(cleaned)


def preview_text(
    text: str,
    *,
    limit: int = 200,
    project_root: str | None = None,
    app_path: str | None = None,
    secret_values: list[str] | None = None,
) -> str:
    cleaned = " ".join((text or "").split())
    cleaned = redact_text(cleaned, secret_values or [])
    cleaned = scrub_text(cleaned, project_root=project_root, app_path=app_path)
    cleaned = _scrub_inline_paths(cleaned)
    if len(cleaned) > limit:
        return cleaned[:limit]
    return cleaned


def _suppress_headers_footers(text: str) -> str:
    if "\f" not in text:
        return text
    pages = text.split("\f")
    if len(pages) <= 1:
        return text
    headers = _common_edge_lines(pages, position="start")
    footers = _common_edge_lines(pages, position="end")
    cleaned_pages = []
    for page in pages:
        lines = page.splitlines()
        while lines and lines[0].strip() in headers:
            lines.pop(0)
        while lines and lines[-1].strip() in footers:
            lines.pop()
        cleaned_pages.append("\n".join(lines))
    return "\f".join(cleaned_pages)


def _common_edge_lines(pages: list[str], *, position: str) -> set[str]:
    counts: dict[str, int] = {}
    for page in pages:
        lines = [line.strip() for line in page.splitlines() if line.strip()]
        if not lines:
            continue
        edge = lines[0] if position == "start" else lines[-1]
        counts[edge] = counts.get(edge, 0) + 1
    threshold = max(2, len(pages) // 2 + 1)
    return {line for line, count in counts.items() if count >= threshold}


def _scrub_inline_paths(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        value = match.group(0)
        for prefix in _SAFE_PREFIXES:
            if value.startswith(prefix):
                return value
        return "<path>"

    return _INLINE_POSIX_PATH.sub(replace, text)


def _native_normalize_text(text: str) -> str | None:
    from namel3ss.runtime.native import NativeStatus, native_normalize

    outcome = native_normalize(text.encode("utf-8"))
    if outcome.status != NativeStatus.OK or outcome.payload is None:
        return None
    try:
        return outcome.payload.decode("utf-8")
    except UnicodeDecodeError:
        return None


__all__ = ["normalize_text", "preview_text", "sanitize_text"]
