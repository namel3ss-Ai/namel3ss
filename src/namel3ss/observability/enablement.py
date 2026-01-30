from __future__ import annotations

import os
from typing import Mapping

from namel3ss.observability.context import ObservabilityContext


ENV_OBSERVABILITY = "N3_OBSERVABILITY"
_TRUTHY = {"1", "true", "yes", "on"}


def observability_enabled(*, env: Mapping[str, str] | None = None, explicit: bool | None = None) -> bool:
    if explicit is not None:
        return bool(explicit)
    source = env or os.environ
    value = source.get(ENV_OBSERVABILITY, "")
    return value.strip().lower() in _TRUTHY


def resolve_observability_context(
    observability: ObservabilityContext | None,
    *,
    project_root: str | None,
    app_path: str | None,
    config=None,
    enabled: bool | None = None,
) -> tuple[ObservabilityContext | None, bool]:
    if observability is not None:
        return observability, False
    if not observability_enabled(explicit=enabled):
        return None, False
    return (
        ObservabilityContext.from_config(
            project_root=project_root,
            app_path=app_path,
            config=config,
        ),
        True,
    )


__all__ = ["ENV_OBSERVABILITY", "observability_enabled", "resolve_observability_context"]
