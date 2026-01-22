from __future__ import annotations

import difflib
from typing import Iterable

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


UI_PRESET_FIELDS: tuple[str, ...] = ("theme", "accent_color", "density", "motion", "shape", "surface")

UI_PRESETS: dict[str, dict[str, str]] = {
    "clarity": {
        "theme": "light",
        "accent_color": "blue",
        "density": "comfortable",
        "motion": "subtle",
        "shape": "rounded",
        "surface": "flat",
    },
    "calm": {
        "theme": "paper",
        "accent_color": "neutral",
        "density": "spacious",
        "motion": "subtle",
        "shape": "soft",
        "surface": "flat",
    },
    "focus": {
        "theme": "white",
        "accent_color": "indigo",
        "density": "compact",
        "motion": "none",
        "shape": "sharp",
        "surface": "outlined",
    },
    "signal": {
        "theme": "midnight",
        "accent_color": "cyan",
        "density": "comfortable",
        "motion": "subtle",
        "shape": "rounded",
        "surface": "raised",
    },
}


def preset_names() -> tuple[str, ...]:
    return tuple(UI_PRESETS.keys())


def validate_ui_preset(value: str, *, line: int | None, column: int | None) -> str:
    if value in UI_PRESETS:
        return value
    _raise_unknown_preset(value, line=line, column=column)
    return value


def resolve_ui_preset(value: str, *, line: int | None = None, column: int | None = None) -> dict[str, str]:
    preset = UI_PRESETS.get(value)
    if preset is None:
        _raise_unknown_preset(value, line=line, column=column)
    return dict(preset)


def _raise_unknown_preset(value: str, *, line: int | None, column: int | None) -> None:
    suggestion = _closest(value, UI_PRESETS.keys())
    fix = f'Did you mean "{suggestion}"?' if suggestion else "Use a supported ui preset."
    allowed = ", ".join(UI_PRESETS.keys())
    raise Namel3ssError(
        build_guidance_message(
            what=f"Unknown ui preset '{value}'.",
            why=f"Allowed presets: {allowed}.",
            fix=fix,
            example='ui:\n  preset is "clarity"',
        ),
        line=line,
        column=column,
    )


def _closest(value: str, choices: Iterable[str]) -> str | None:
    matches = difflib.get_close_matches(value, list(choices), n=1, cutoff=0.6)
    return matches[0] if matches else None


__all__ = ["UI_PRESET_FIELDS", "UI_PRESETS", "preset_names", "resolve_ui_preset", "validate_ui_preset"]
