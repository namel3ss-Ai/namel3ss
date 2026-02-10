from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from namel3ss.errors.base import Namel3ssError

PUBLIC_API_SURFACE: Mapping[str, tuple[str, ...]] = {
    "grammar": (
        "namel3ss.parser",
        "namel3ss.lexer",
    ),
    "manifest": (
        "namel3ss.ui.manifest",
        "namel3ss.ui.manifest.layout_schema",
        "namel3ss.ui.manifest.actions",
    ),
    "runtime_contracts": (
        "namel3ss.runtime.contracts",
        "namel3ss.runtime.ui_api",
    ),
    "plugin_api": (
        "namel3ss.plugins.plugin_api",
    ),
    "cli": (
        "namel3ss.cli.main",
        "namel3ss.cli.build_command",
        "namel3ss.cli.deploy_command",
        "namel3ss.cli.create_mode",
    ),
}


@dataclass(frozen=True)
class PublicApiDeclaration:
    category: str
    module_prefixes: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "category": self.category,
            "module_prefixes": list(self.module_prefixes),
        }


def public_api_declarations() -> tuple[PublicApiDeclaration, ...]:
    declarations = []
    for category in sorted(PUBLIC_API_SURFACE.keys()):
        declarations.append(
            PublicApiDeclaration(
                category=category,
                module_prefixes=tuple(sorted(PUBLIC_API_SURFACE[category])),
            )
        )
    return tuple(declarations)


def normalize_module_name(module_name: str | None) -> str:
    return str(module_name or "").strip()


def public_module_prefixes() -> tuple[str, ...]:
    prefixes: list[str] = []
    for declaration in public_api_declarations():
        prefixes.extend(declaration.module_prefixes)
    return tuple(sorted(set(prefixes)))


def is_public_module(module_name: str) -> bool:
    module = normalize_module_name(module_name)
    if not module:
        return False
    for prefix in public_module_prefixes():
        if module == prefix or module.startswith(f"{prefix}."):
            return True
    return False


def assert_public_module(module_name: str) -> None:
    if not is_public_module(module_name):
        raise Namel3ssError(
            f"Module '{module_name}' is not part of the frozen public API surface."
        )


__all__ = [
    "PUBLIC_API_SURFACE",
    "PublicApiDeclaration",
    "assert_public_module",
    "is_public_module",
    "normalize_module_name",
    "public_api_declarations",
    "public_module_prefixes",
]
