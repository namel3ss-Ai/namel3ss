from __future__ import annotations

from .normalize import stable_bullets, stable_truncate


def render_see(pack: dict) -> str:
    pages = pack.get("pages") or []
    actions = pack.get("actions") or []
    what_not = pack.get("what_not") or []

    lines: list[str] = []
    lines.append("What the user sees")
    lines.append("")
    lines.append("Pages")
    if not pages:
        lines.extend(stable_bullets(["No pages were recorded."]))
    else:
        lines.extend(stable_bullets([_page_summary(page) for page in pages]))

    for page in pages:
        lines.append("")
        lines.append(f"On page \"{page.get('name')}\"")
        elements = page.get("elements") or []
        if not elements:
            lines.extend(stable_bullets(["No elements were recorded."]))
            continue
        lines.extend(_render_elements(elements))

    lines.append("")
    lines.append("Actions")
    if not actions:
        lines.extend(stable_bullets(["No actions were recorded."]))
    else:
        lines.extend(_render_actions(actions))

    lines.append("")
    lines.append("What the user does not see")
    if what_not:
        lines.extend(stable_bullets([stable_truncate(str(entry)) for entry in what_not]))
    else:
        lines.extend(stable_bullets(["No explicit hidden rules were recorded for this ui."]))
    return "\n".join(lines).rstrip()


def _page_summary(page: dict) -> str:
    name = page.get("name") or ""
    elements = page.get("elements") or []
    return f"{name} ({len(elements)} items)"


def _render_elements(elements: list[dict]) -> list[str]:
    lines: list[str] = []
    for element in elements:
        lines.append(_element_header(element))
        if element.get("enabled") is not None:
            enabled_text = "yes" if element.get("enabled") else "no"
            lines.append(f"  - enabled: {enabled_text}")
        if element.get("bound_to"):
            lines.append(f"  - bound to: {stable_truncate(str(element.get('bound_to')))}")
        for reason in element.get("reasons") or []:
            lines.append(f"  - because: {stable_truncate(str(reason))}")
    return lines


def _element_header(element: dict) -> str:
    kind = element.get("kind") or "item"
    label = element.get("label")
    if label:
        return f"- {kind}: \"{stable_truncate(str(label))}\""
    return f"- {kind}"


def _render_actions(actions: list[dict]) -> list[str]:
    lines: list[str] = []
    for action in actions:
        action_id = action.get("id") or ""
        status = action.get("status") or "unknown"
        lines.append(f"- {action_id}: {status}")
        if status != "available":
            for reason in action.get("reasons") or []:
                lines.append(f"  - why: {stable_truncate(str(reason))}")
    return lines


__all__ = ["render_see"]
