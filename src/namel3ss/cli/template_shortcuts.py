from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TemplateShortcut:
    command: str
    name: str
    path: str
    description: str


TEMPLATE_SHORTCUTS: tuple[TemplateShortcut, ...] = (
    TemplateShortcut(
        command="kb",
        name="knowledge",
        path="templates/knowledge",
        description="Knowledge template",
    ),
)


def find_template_shortcut(command: str) -> TemplateShortcut | None:
    for shortcut in TEMPLATE_SHORTCUTS:
        if shortcut.command == command:
            return shortcut
    return None


def render_template_shortcut(shortcut: TemplateShortcut) -> str:
    lines = [
        "Template reference:",
        f"  command: {shortcut.command}",
        f"  name: {shortcut.name}",
        f"  path: {shortcut.path}",
    ]
    return "\n".join(lines)


__all__ = ["TEMPLATE_SHORTCUTS", "TemplateShortcut", "find_template_shortcut", "render_template_shortcut"]
