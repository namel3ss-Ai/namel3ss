from __future__ import annotations

from namel3ss.ingestion.keywords import extract_keywords, keyword_matches, normalize_keywords
from namel3ss.ingestion.normalize import sanitize_text


def safe_keyword_overlap(
    entry: dict,
    text_value: str,
    query_keywords: list[str],
    *,
    project_root: str | None,
    app_path: str | None,
    secret_values: list[str] | None,
) -> int:
    if not query_keywords:
        return 0
    keywords = normalize_keywords(entry.get("keywords"))
    if keywords is None:
        cleaned = sanitize_text(text_value, project_root=project_root, app_path=app_path, secret_values=secret_values)
        keywords = extract_keywords(cleaned) if cleaned else []
    matches = keyword_matches(query_keywords, keywords)
    return len(matches)


__all__ = ["safe_keyword_overlap"]
