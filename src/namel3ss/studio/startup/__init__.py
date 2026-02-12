# Re-export keeps existing `from namel3ss.studio.startup import ...` imports stable.
from namel3ss.studio.startup.startup_validation import (
    reset_renderer_registry_startup_cache,
    validate_renderer_registry_startup,
)

__all__ = ["reset_renderer_registry_startup_cache", "validate_renderer_registry_startup"]
