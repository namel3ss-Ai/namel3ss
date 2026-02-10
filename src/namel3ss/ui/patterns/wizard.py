from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Iterable

from namel3ss.errors.base import Namel3ssError


@dataclass(frozen=True)
class WizardPatternConfig:
    name: str = "wizard_flow"
    title: str = "Guided Setup"
    sections: tuple[str, ...] = ("Source", "Validation", "Review")
    state_path: str = "wizardState.currentStep"


def build_wizard_pattern(config: WizardPatternConfig | None = None) -> dict[str, object]:
    resolved = config or WizardPatternConfig()
    if not resolved.sections:
        raise Namel3ssError("wizard pattern requires at least one section.")
    if any(not isinstance(section, str) or not section.strip() for section in resolved.sections):
        raise Namel3ssError("wizard sections must be non-empty text values.")
    if not _valid_state_path(resolved.state_path):
        raise Namel3ssError(f'Invalid wizard state path "{resolved.state_path}".')
    slug = _slugify(resolved.name)
    ids = _pattern_ids(slug)

    actions = {
        ids["action_back"]: {
            "id": ids["action_back"],
            "type": "component.wizard.back",
            "target": resolved.state_path,
            "payload": {},
            "order": 0,
            "line": 0,
            "column": 0,
        },
        ids["action_next"]: {
            "id": ids["action_next"],
            "type": "component.wizard.next",
            "target": resolved.state_path,
            "payload": {},
            "order": 1,
            "line": 0,
            "column": 0,
        },
        ids["action_submit"]: {
            "id": ids["action_submit"],
            "type": "component.wizard.submit",
            "target": "flow.wizard.submit",
            "payload": {"state_path": resolved.state_path},
            "order": 2,
            "line": 0,
            "column": 0,
        },
    }
    return {
        "pattern": "wizard",
        "name": resolved.name,
        "title": resolved.title,
        "state": [{"path": resolved.state_path, "default": 0}],
        "layout": [
            {
                "type": "layout.main",
                "id": ids["main"],
                "bindings": {"on_click": None, "keyboard_shortcut": None, "selected_item": None},
                "children": [
                    {
                        "type": "component.form",
                        "id": ids["form"],
                        "name": "wizard_form",
                        "wizard": True,
                        "sections": list(resolved.sections),
                        "children": [],
                        "bindings": {"on_click": None, "keyboard_shortcut": None, "selected_item": None},
                        "line": 0,
                        "column": 0,
                    },
                    {
                        "type": "layout.sticky",
                        "id": ids["sticky"],
                        "position": "bottom",
                        "visible": True,
                        "bindings": {"on_click": None, "keyboard_shortcut": None, "selected_item": None},
                        "children": [
                            {
                                "type": "component.literal",
                                "id": ids["back_label"],
                                "text": "Back",
                                "bindings": {
                                    "on_click": ids["action_back"],
                                    "keyboard_shortcut": None,
                                    "selected_item": None,
                                },
                                "line": 0,
                                "column": 0,
                            },
                            {
                                "type": "component.literal",
                                "id": ids["next_label"],
                                "text": "Next",
                                "bindings": {
                                    "on_click": ids["action_next"],
                                    "keyboard_shortcut": None,
                                    "selected_item": None,
                                },
                                "line": 0,
                                "column": 0,
                            },
                            {
                                "type": "component.literal",
                                "id": ids["submit_label"],
                                "text": "Submit",
                                "bindings": {
                                    "on_click": ids["action_submit"],
                                    "keyboard_shortcut": "ctrl+enter",
                                    "selected_item": None,
                                },
                                "line": 0,
                                "column": 0,
                            },
                        ],
                        "line": 0,
                        "column": 0,
                    },
                ],
                "line": 0,
                "column": 0,
            }
        ],
        "actions": actions,
    }


def _pattern_ids(slug: str) -> dict[str, str]:
    return {
        "main": _stable_id(slug, "layout.main", (0,)),
        "form": _stable_id(slug, "component.form", (0, 0)),
        "sticky": _stable_id(slug, "layout.sticky", (0, 1)),
        "back_label": _stable_id(slug, "component.literal", (0, 1, 0)),
        "next_label": _stable_id(slug, "component.literal", (0, 1, 1)),
        "submit_label": _stable_id(slug, "component.literal", (0, 1, 2)),
        "action_back": _stable_action_id(slug, "back"),
        "action_next": _stable_action_id(slug, "next"),
        "action_submit": _stable_action_id(slug, "submit"),
    }


def _stable_id(slug: str, kind: str, path: Iterable[int]) -> str:
    encoded_path = ".".join(str(part) for part in path)
    payload = f"{slug}|{kind}|{encoded_path}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    return f"pattern.{slug}.{kind.replace('.', '_')}.{digest}"


def _stable_action_id(slug: str, name: str) -> str:
    payload = f"{slug}|{name}|action"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:10]
    return f"pattern.{slug}.action.{name}.{digest}"


def _valid_state_path(path: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*", path))


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    result = cleaned.strip("_")
    return result or "wizard_flow"


__all__ = ["WizardPatternConfig", "build_wizard_pattern"]
