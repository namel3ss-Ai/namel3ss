from __future__ import annotations

BUILTIN_CAPABILITIES = (
    "http",
    "jobs",
    "files",
    "scheduling",
    "uploads",
    "secrets",
    "embedding",
    "vision",
    "speech",
    "huggingface",
    "local_runner",
    "vision_gen",
    "third_party_apis",
    "dependency_management",
    "training",
    "streaming",
    "performance",
    "versioning_quality_mlops",
    "performance_scalability",
    "decoupled_ui_api",
    "ecosystem_developer_experience",
    "security_compliance",
    "custom_ui",
    "ui.custom_layouts",
    "ui.rag_patterns",
    "ui.theming",
    "ui.i18n",
    "ui.plugins",
    "ui.slider",
    "ui.tooltip",
    "ui.citations_enhanced",
    "composition.includes",
    "diagnostics.trace",
    "ui_layout",
    "ui_rag",
    "ui_theme",
    "ui_navigation",
    "ui_state",
    "app_permissions",
    "app_packaging",
    "custom_theme",
    "theme_editor",
    "dev_tools",
    "plugin_registry",
    "responsive_design",
    "sandbox",
    "service",
    "multi_user",
    "remote_studio",
    "extension_hooks",
    "hook_execution",
    "extension_trust",
    "remote_registry",
)


def normalize_builtin_capability(name: str | None) -> str | None:
    if not isinstance(name, str):
        return None
    value = name.strip().lower()
    if value in BUILTIN_CAPABILITIES:
        return value
    return None


def normalize_capability_tokens(values: tuple[str, ...] | list[str] | set[str] | None) -> tuple[str, ...]:
    if not values:
        return ()
    normalized: list[str] = []
    for item in values:
        token = normalize_builtin_capability(item if isinstance(item, str) else None)
        if token is not None:
            normalized.append(token)
    return tuple(sorted(set(normalized)))


def is_builtin_capability(name: str | None) -> bool:
    return normalize_builtin_capability(name) is not None


def has_ui_theming_capability(values: tuple[str, ...] | list[str] | set[str] | None) -> bool:
    normalized = set(normalize_capability_tokens(values))
    return "ui.theming" in normalized or "ui_theme" in normalized


__all__ = [
    "BUILTIN_CAPABILITIES",
    "has_ui_theming_capability",
    "is_builtin_capability",
    "normalize_builtin_capability",
    "normalize_capability_tokens",
]
