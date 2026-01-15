from __future__ import annotations

from namel3ss.validation import ValidationMode
from namel3ss.runtime.identity.context import resolve_identity
from namel3ss.ui.manifest import build_manifest


def build_static_manifest(
    program_ir,
    *,
    config,
    state: dict | None = None,
    store=None,
    warnings: list | None = None,
    **manifest_kwargs,
) -> dict:
    """Canonical static manifest builder shared between CLI and Studio surfaces."""
    warnings = warnings or []
    identity = resolve_identity(
        config,
        getattr(program_ir, "identity", None),
        mode=ValidationMode.STATIC,
        warnings=warnings,
    )
    return build_manifest(
        program_ir,
        state=state if isinstance(state, dict) else {},
        store=store,
        identity=identity,
        mode=ValidationMode.STATIC,
        warnings=warnings,
        **manifest_kwargs,
    )


__all__ = ["build_static_manifest"]
