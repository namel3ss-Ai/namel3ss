from __future__ import annotations

DISPLAY_MODE_PRODUCTION = "production"
DISPLAY_MODE_STUDIO = "studio"

DISPLAY_MODES = (
    DISPLAY_MODE_PRODUCTION,
    DISPLAY_MODE_STUDIO,
)


def normalize_display_mode(value: str | None, *, default: str = DISPLAY_MODE_STUDIO) -> str:
    token = (value or default).strip().lower()
    if token in DISPLAY_MODES:
        return token
    valid = ", ".join(DISPLAY_MODES)
    raise ValueError(f"Unknown display mode '{value}'. Expected one of: {valid}.")


def is_display_mode(value: str | None) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in DISPLAY_MODES


__all__ = [
    "DISPLAY_MODE_PRODUCTION",
    "DISPLAY_MODE_STUDIO",
    "DISPLAY_MODES",
    "is_display_mode",
    "normalize_display_mode",
]
