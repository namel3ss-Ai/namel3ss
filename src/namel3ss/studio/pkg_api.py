from __future__ import annotations

from namel3ss.errors.guidance import build_guidance_message
from namel3ss.pkg.index import get_entry, load_index, search_index


def search_pkg_index_payload(query: str) -> dict:
    if not query:
        return {
            "schema_version": 1,
            "ok": False,
            "error": build_guidance_message(
                what="Search query is required.",
                why="Package discovery needs a search term.",
                fix="Enter a keyword and try again.",
                example="auth",
            ),
        }
    entries = load_index()
    results = search_index(query, entries)
    return {
        "schema_version": 1,
        "ok": True,
        "query": query,
        "count": len(results),
        "results": [result.to_dict() for result in results],
    }


def get_pkg_info_payload(name: str) -> dict:
    if not name:
        return {
            "schema_version": 1,
            "ok": False,
            "error": build_guidance_message(
                what="Package name is required.",
                why="Package info needs a name from the index.",
                fix="Enter a package name and retry.",
                example="auth-basic",
            ),
        }
    entries = load_index()
    entry = get_entry(name, entries)
    if entry is None:
        return {
            "schema_version": 1,
            "ok": False,
            "error": build_guidance_message(
                what=f"Package '{name}' is not in the index.",
                why="The official index has no matching entry.",
                fix="Check the spelling or use a GitHub source spec.",
                example="n3 pkg add github:owner/repo@v0.1.0",
            ),
        }
    payload = entry.to_dict()
    payload["install"] = f"n3 pkg add {entry.source_spec()}"
    payload["schema_version"] = 1
    payload["ok"] = True
    return payload


__all__ = ["get_pkg_info_payload", "search_pkg_index_payload"]
