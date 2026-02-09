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


def is_builtin_capability(name: str | None) -> bool:
    return normalize_builtin_capability(name) is not None


__all__ = ["BUILTIN_CAPABILITIES", "is_builtin_capability", "normalize_builtin_capability"]
