from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from namel3ss.ast.base import Node


@dataclass
class RouteField(Node):
    name: str
    type_name: str
    type_was_alias: bool = False
    raw_type_name: Optional[str] = None
    type_line: Optional[int] = None
    type_column: Optional[int] = None


@dataclass
class RouteDefinition(Node):
    name: str
    path: str
    method: str
    parameters: Dict[str, RouteField]
    request: Optional[Dict[str, RouteField]]
    response: Dict[str, RouteField]
    flow_name: str
    upload: Optional[bool] = None
    generated: bool = False


__all__ = ["RouteDefinition", "RouteField"]
