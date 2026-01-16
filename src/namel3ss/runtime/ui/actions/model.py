from __future__ import annotations

from namel3ss.ir import nodes as ir

SUBMIT_RESERVED_KEYS = {"values", "errors", "ok", "result", "state", "traces"}


def page_slug_from_action(action_id: str) -> str | None:
    parts = action_id.split(".")
    if len(parts) >= 2 and parts[0] == "page":
        return parts[1]
    return None


def page_name_for_slug(manifest: dict, slug: str | None) -> str | None:
    if not slug:
        return None
    for page in manifest.get("pages", []):
        if isinstance(page, dict) and page.get("slug") == slug:
            name = page.get("name")
            return str(name) if isinstance(name, str) else None
    return None


def page_decl_for_name(program_ir: ir.Program, page_name: str | None) -> ir.Page | None:
    if not page_name:
        return None
    for page in getattr(program_ir, "pages", []):
        if page.name == page_name:
            return page
    return None


def page_subject(page_name: str | None, page_slug: str | None) -> str:
    if page_name:
        return f'page "{page_name}"'
    if page_slug:
        return f'page "{page_slug}"'
    return "page"


def form_flow_name(page_slug: str | None, record: str) -> str:
    slug = page_slug or "page"
    return f"page.{slug}.form.{record}"


__all__ = [
    "SUBMIT_RESERVED_KEYS",
    "form_flow_name",
    "page_decl_for_name",
    "page_name_for_slug",
    "page_slug_from_action",
    "page_subject",
]
