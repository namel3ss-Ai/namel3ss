from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ThemeDefinition:
    preset: str | None = None
    brand_palette: dict[str, str] = field(default_factory=dict)
    tokens: dict[str, str] = field(default_factory=dict)
    responsive_tokens: dict[str, tuple[int, ...]] = field(default_factory=dict)
    harmonize: bool = False
    allow_low_contrast: bool = False
    density: str | None = None
    motion: str | None = None
    shape: str | None = None
    surface: str | None = None
    line: int | None = None
    column: int | None = None


@dataclass(frozen=True)
class ResolvedTheme:
    definition: ThemeDefinition
    tokens: dict[str, str]
    ui_overrides: dict[str, str]
    responsive_tokens: dict[str, tuple[int, ...]] = field(default_factory=dict)
