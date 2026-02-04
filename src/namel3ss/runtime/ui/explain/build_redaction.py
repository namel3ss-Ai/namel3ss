from __future__ import annotations


def _element_label(kind: str, element: dict) -> str | None:
    if kind in {"title", "text"}:
        return element.get("value")
    if kind in {"story", "story_step"}:
        return element.get("title")
    if kind in {"button", "link", "section", "card", "tab", "modal", "drawer"}:
        return element.get("label")
    if kind in {"messages", "citations", "memory"}:
        return element.get("source")
    if kind == "composer":
        return element.get("flow")
    if kind == "input":
        return element.get("name")
    if kind == "thinking":
        return element.get("when")
    if kind == "image":
        return element.get("alt") or element.get("media_name") or element.get("src")
    if kind == "chart":
        return element.get("explain") or element.get("record") or element.get("source")
    if kind == "upload":
        return element.get("name")
    return None


def _element_fix_hint(kind: str, element: dict) -> str | None:
    if kind == "image":
        if element.get("missing") and element.get("fix_hint"):
            return element.get("fix_hint")
        return None
    if kind == "story_step":
        image = element.get("image")
        if isinstance(image, dict) and image.get("missing") and image.get("fix_hint"):
            return image.get("fix_hint")
    return None


def _bound_to(kind: str, element: dict) -> str | None:
    if kind in {"form", "table", "list"}:
        record = element.get("record")
        if record:
            return f"record:{record}"
    if kind in {"messages", "citations", "memory"}:
        source = element.get("source")
        if source:
            return source
    if kind == "thinking":
        when = element.get("when")
        if when:
            return when
    if kind == "composer":
        flow = element.get("flow")
        if flow:
            return f"flow:{flow}"
    if kind == "input":
        flow = element.get("action", {}).get("flow") if isinstance(element.get("action"), dict) else None
        if flow:
            return f"flow:{flow}"
    if kind == "link":
        target = element.get("target")
        if target:
            return f"page:{target}"
    if kind == "chart":
        record = element.get("record")
        if record:
            return f"record:{record}"
        source = element.get("source")
        if source:
            return source
    return None


__all__ = ["_bound_to", "_element_fix_hint", "_element_label"]
