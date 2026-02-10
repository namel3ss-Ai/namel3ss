from __future__ import annotations

from dataclasses import dataclass

from namel3ss.errors.base import Namel3ssError

INTERNAL_API_PREFIXES: tuple[str, ...] = (
    "namel3ss.ast",
    "namel3ss.ir",
    "namel3ss.parser.core",
    "namel3ss.runtime.executor",
    "namel3ss.runtime.tools.executor",
    "namel3ss.ui.manifest.elements",
)

EXTERNAL_CONSUMER_PREFIXES: tuple[str, ...] = (
    "app.",
    "apps.",
    "plugins.",
    "template_plugins.",
    "app_plugins.",
)


@dataclass(frozen=True)
class BoundaryViolation:
    importer: str
    imported: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {
            "importer": self.importer,
            "imported": self.imported,
            "message": self.message,
        }


def normalize_module_name(module_name: str | None) -> str:
    return str(module_name or "").strip()


def is_internal_module(module_name: str) -> bool:
    module = normalize_module_name(module_name)
    if not module:
        return False
    for prefix in INTERNAL_API_PREFIXES:
        if module == prefix or module.startswith(f"{prefix}."):
            return True
    return False


def detect_boundary_violation(importer_module: str, imported_module: str) -> BoundaryViolation | None:
    importer = normalize_module_name(importer_module)
    imported = normalize_module_name(imported_module)
    if not importer or not imported:
        return None
    if not is_internal_module(imported):
        return None
    if not _is_external_consumer(importer):
        return None
    return BoundaryViolation(
        importer=importer,
        imported=imported,
        message=(
            f"External consumer '{importer}' cannot import internal module '{imported}'. "
            "Use the documented public API surface."
        ),
    )


def assert_import_allowed(importer_module: str, imported_module: str) -> None:
    violation = detect_boundary_violation(importer_module, imported_module)
    if violation is None:
        return
    raise Namel3ssError(violation.message)


def _is_external_consumer(importer_module: str) -> bool:
    module = normalize_module_name(importer_module)
    for prefix in EXTERNAL_CONSUMER_PREFIXES:
        if module == prefix.rstrip(".") or module.startswith(prefix):
            return True
    return False


__all__ = [
    "BoundaryViolation",
    "EXTERNAL_CONSUMER_PREFIXES",
    "INTERNAL_API_PREFIXES",
    "assert_import_allowed",
    "detect_boundary_violation",
    "is_internal_module",
    "normalize_module_name",
]
