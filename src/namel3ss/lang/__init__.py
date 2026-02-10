"""Language-level API and governance helpers for Namel3ss."""

from namel3ss.lang.capabilities import (
    BUILTIN_CAPABILITIES,
    has_ui_theming_capability,
    is_builtin_capability,
    normalize_builtin_capability,
    normalize_capability_tokens,
)
from namel3ss.lang.deprecation import (
    DEPRECATION_RULES,
    DeprecationRule,
    append_capability_deprecation_warnings,
    deprecation_rules,
    find_capability_deprecations,
)
from namel3ss.lang.internal_api import (
    BoundaryViolation,
    EXTERNAL_CONSUMER_PREFIXES,
    INTERNAL_API_PREFIXES,
    assert_import_allowed,
    detect_boundary_violation,
    is_internal_module,
)
from namel3ss.lang.public_api import (
    PUBLIC_API_SURFACE,
    PublicApiDeclaration,
    assert_public_module,
    is_public_module,
    public_api_declarations,
    public_module_prefixes,
)

__all__ = [
    "BUILTIN_CAPABILITIES",
    "BoundaryViolation",
    "DEPRECATION_RULES",
    "DeprecationRule",
    "EXTERNAL_CONSUMER_PREFIXES",
    "INTERNAL_API_PREFIXES",
    "PUBLIC_API_SURFACE",
    "PublicApiDeclaration",
    "append_capability_deprecation_warnings",
    "assert_import_allowed",
    "assert_public_module",
    "deprecation_rules",
    "detect_boundary_violation",
    "find_capability_deprecations",
    "has_ui_theming_capability",
    "is_builtin_capability",
    "is_internal_module",
    "is_public_module",
    "normalize_builtin_capability",
    "normalize_capability_tokens",
    "public_api_declarations",
    "public_module_prefixes",
]
