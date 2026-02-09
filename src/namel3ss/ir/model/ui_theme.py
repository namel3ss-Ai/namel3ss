from __future__ import annotations

from dataclasses import dataclass

from namel3ss.ir.model.base import Node


@dataclass
class ThemeTokens(Node):
    size: str | None = None
    radius: str | None = None
    density: str | None = None
    font: str | None = None
    color_scheme: str | None = None


@dataclass
class ThemeTokenOverrides(Node):
    size: str | None = None
    radius: str | None = None
    density: str | None = None
    font: str | None = None


__all__ = ["ThemeTokenOverrides", "ThemeTokens"]
