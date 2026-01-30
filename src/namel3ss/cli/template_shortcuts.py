from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TemplateShortcut:
    command: str
    name: str
    path: str
    description: str


TEMPLATE_LIST_COMMAND = "list"

TEMPLATE_SHORTCUTS: tuple[TemplateShortcut, ...] = (
    TemplateShortcut(
        command="kb",
        name="knowledge",
        path="templates/knowledge",
        description="Knowledge template",
    ),
    TemplateShortcut(
        command="ops",
        name="operations",
        path="templates/operations",
        description="Operations template",
    ),
    TemplateShortcut(
        command="aid",
        name="support",
        path="templates/support",
        description="Support template",
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


def render_template_list() -> str:
    shortcuts = sorted(TEMPLATE_SHORTCUTS, key=lambda item: item.name)
    names = [shortcut.name for shortcut in shortcuts]
    commands = [shortcut.command for shortcut in shortcuts]
    max_name = max(len(name) for name in names)
    max_command = max(len(command) for command in commands)
    lines = ["Templates:"]
    for shortcut in shortcuts:
        name = shortcut.name.ljust(max_name)
        command = shortcut.command.ljust(max_command)
        lines.append(f"  {name} {command} {shortcut.path}")
    return "\n".join(lines)


__all__ = [
    "TEMPLATE_LIST_COMMAND",
    "TEMPLATE_SHORTCUTS",
    "TemplateShortcut",
    "find_template_shortcut",
    "render_template_list",
    "render_template_shortcut",
]
