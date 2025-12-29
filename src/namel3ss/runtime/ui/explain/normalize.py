from __future__ import annotations

import json
from pathlib import Path


def stable_join(items: list[str], sep: str = ", ") -> str:
    return sep.join(items)


def stable_bullets(lines: list[str]) -> list[str]:
    return [line if line.startswith("- ") else f"- {line}" for line in lines]


def stable_truncate(text: str, limit: int = 120) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def build_plain_text(pack: dict) -> str:
    pages = pack.get("pages") or []
    actions = pack.get("actions") or []
    elements_total = _element_total(pages)

    lines: list[str] = []
    lines.append(f"summary: {pack.get('summary') or ''}")
    lines.append(f"api_version: {pack.get('api_version') or ''}")
    lines.append(f"pages.count: {len(pages)}")
    lines.append(f"elements.count: {elements_total}")
    lines.append(f"actions.count: {len(actions)}")

    for idx, page in enumerate(pages, start=1):
        page_name = page.get("name") or ""
        elements = page.get("elements") or []
        lines.append(f"page.{idx}.name: {page_name}")
        lines.append(f"page.{idx}.elements: {len(elements)}")

    for idx, action in enumerate(actions, start=1):
        lines.append(f"action.{idx}.id: {action.get('id')}")
        lines.append(f"action.{idx}.status: {action.get('status')}")
        if action.get("requires"):
            lines.append(f"action.{idx}.requires: {action.get('requires')}")

    element_index = 1
    for page in pages:
        elements = page.get("elements") or []
        for element in elements:
            prefix = f"element.{element_index}"
            lines.append(f"{prefix}.id: {element.get('id')}")
            lines.append(f"{prefix}.kind: {element.get('kind')}")
            if element.get("label"):
                lines.append(f"{prefix}.label: {element.get('label')}")
            if element.get("enabled") is not None:
                lines.append(f"{prefix}.enabled: {element.get('enabled')}")
            if element.get("bound_to"):
                lines.append(f"{prefix}.bound_to: {element.get('bound_to')}")
            element_index += 1

    what_not = pack.get("what_not") or []
    lines.append(f"what_not.count: {len(what_not)}")
    for idx, entry in enumerate(what_not, start=1):
        lines.append(f"what_not.{idx}: {entry}")

    return "\n".join(lines)


def write_last_ui(root: Path, pack: dict, plain_text: str, text: str) -> None:
    ui_dir = root / ".namel3ss" / "ui"
    ui_dir.mkdir(parents=True, exist_ok=True)
    (ui_dir / "last.json").write_text(_stable_json(pack), encoding="utf-8")
    (ui_dir / "last.plain").write_text(plain_text.rstrip() + "\n", encoding="utf-8")
    (ui_dir / "last.see.txt").write_text(text.rstrip() + "\n", encoding="utf-8")


def _stable_json(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _element_total(pages: list[dict]) -> int:
    total = 0
    for page in pages:
        elements = page.get("elements") or []
        total += len(elements)
    return total


__all__ = [
    "build_plain_text",
    "stable_bullets",
    "stable_join",
    "stable_truncate",
    "write_last_ui",
]
