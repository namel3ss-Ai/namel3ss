from __future__ import annotations

from dataclasses import dataclass

from namel3ss.ast.base import Node


@dataclass
class AppPermissionActionDecl(Node):
    action: str
    allowed: bool


@dataclass
class AppPermissionDomainDecl(Node):
    domain: str
    actions: list[AppPermissionActionDecl]


@dataclass
class AppPermissionsDecl(Node):
    domains: list[AppPermissionDomainDecl]


__all__ = ["AppPermissionActionDecl", "AppPermissionDomainDecl", "AppPermissionsDecl"]
