from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from namel3ss.ast.base import Node


@dataclass
class PromptDefinition(Node):
    name: str
    version: str
    text: str
    description: Optional[str] = None


__all__ = ["PromptDefinition"]
