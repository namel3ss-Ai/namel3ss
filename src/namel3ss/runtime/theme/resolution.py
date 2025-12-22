from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class ThemeSetting(str, Enum):
    LIGHT = "light"
    DARK = "dark"
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


def resolve_effective_theme(setting: str, system_available: bool, system_value: Optional[str]) -> EffectiveTheme:
    if setting == ThemeSetting.DARK.value:
        return EffectiveTheme.DARK
    if setting == ThemeSetting.LIGHT.value:
        return EffectiveTheme.LIGHT
    # system
    if system_available and system_value in {ThemeSetting.DARK.value, ThemeSetting.LIGHT.value}:
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
    persisted_normalized = persisted_value if persisted_value in {ThemeSetting.LIGHT.value, ThemeSetting.DARK.value, ThemeSetting.SYSTEM.value} else None

    if allow_override and persist_mode == "file" and persisted_normalized:
        setting_used = persisted_normalized
        source = ThemeSource.PERSISTED
    elif session_theme in {ThemeSetting.LIGHT.value, ThemeSetting.DARK.value, ThemeSetting.SYSTEM.value}:
        setting_used = session_theme
        source = ThemeSource.SESSION
    elif app_setting in {ThemeSetting.LIGHT.value, ThemeSetting.DARK.value, ThemeSetting.SYSTEM.value}:
        setting_used = app_setting
        source = ThemeSource.APP
    else:
        setting_used = ThemeSetting.SYSTEM.value
        source = ThemeSource.FALLBACK

    effective = resolve_effective_theme(setting_used, system_available, system_value)
    if setting_used == ThemeSetting.SYSTEM.value and system_available:
        source = ThemeSource.SYSTEM if source == ThemeSource.APP else source
    return ThemeResolution(setting_used=ThemeSetting(setting_used), effective=effective, source=source, persisted=persisted_normalized)
