from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

from namel3ss.ui.settings import UI_ALLOWED_VALUES, UI_DEFAULTS


class ThemeSetting(str, Enum):
    LIGHT = "light"
    DARK = "dark"
    WHITE = "white"
    BLACK = "black"
    MIDNIGHT = "midnight"
    PAPER = "paper"
    TERMINAL = "terminal"
    ENTERPRISE = "enterprise"
    SYSTEM = "system"


class EffectiveTheme(str, Enum):
    LIGHT = "light"
    DARK = "dark"


class ThemeSource(str, Enum):
    PERSISTED = "persisted"
    SESSION = "session"
    APP = "app"
    SYSTEM = "system"
    FALLBACK = "fallback"


@dataclass
class ThemeResolution:
    setting_used: ThemeSetting
    effective: EffectiveTheme
    source: ThemeSource
    persisted: Optional[str] = None


_DARK_THEMES = {
    ThemeSetting.DARK.value,
    ThemeSetting.BLACK.value,
    ThemeSetting.MIDNIGHT.value,
    ThemeSetting.TERMINAL.value,
}
_LIGHT_THEMES = {
    ThemeSetting.LIGHT.value,
    ThemeSetting.WHITE.value,
    ThemeSetting.PAPER.value,
    ThemeSetting.ENTERPRISE.value,
}


def resolve_effective_theme(setting: str, system_available: bool, system_value: Optional[str]) -> EffectiveTheme:
    if setting in _DARK_THEMES:
        return EffectiveTheme.DARK
    if setting in _LIGHT_THEMES:
        return EffectiveTheme.LIGHT
    if setting == ThemeSetting.SYSTEM.value and system_available and system_value in {ThemeSetting.DARK.value, ThemeSetting.LIGHT.value}:
        return EffectiveTheme.DARK if system_value == ThemeSetting.DARK.value else EffectiveTheme.LIGHT
    return EffectiveTheme.LIGHT


def resolve_initial_theme(
    *,
    allow_override: bool,
    persist_mode: str,
    persisted_value: Optional[str],
    session_theme: Optional[str],
    app_setting: str,
    system_available: bool,
    system_value: Optional[str],
) -> ThemeResolution:
    setting_used: str = app_setting
    source = ThemeSource.APP
    allowed = set(UI_ALLOWED_VALUES.get("theme", ()))
    persisted_normalized = persisted_value if persisted_value in allowed else None

    if allow_override and persist_mode == "file" and persisted_normalized:
        setting_used = persisted_normalized
        source = ThemeSource.PERSISTED
    elif session_theme in allowed:
        setting_used = session_theme
        source = ThemeSource.SESSION
    elif app_setting in allowed:
        setting_used = app_setting
        source = ThemeSource.APP
    else:
        setting_used = UI_DEFAULTS["theme"]
        source = ThemeSource.FALLBACK

    effective = resolve_effective_theme(setting_used, system_available, system_value)
    if setting_used == ThemeSetting.SYSTEM.value and system_available:
        source = ThemeSource.SYSTEM if source == ThemeSource.APP else source
    try:
        setting_enum = ThemeSetting(setting_used)
    except ValueError:
        setting_enum = ThemeSetting(UI_DEFAULTS["theme"])
    return ThemeResolution(setting_used=setting_enum, effective=effective, source=source, persisted=persisted_normalized)
