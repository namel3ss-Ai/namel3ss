from __future__ import annotations

from namel3ss.config.loader import load_config
from namel3ss.runtime.identity.context import resolve_identity
from namel3ss.runtime.storage.factory import resolve_store
from namel3ss.ui.export.actions import build_actions_export
from namel3ss.ui.export.schema import build_schema_export
from namel3ss.ui.export.ui import build_ui_export
from namel3ss.ui.manifest import build_manifest
from namel3ss.validation import ValidationMode


def build_contract_manifest(
    program_ir,
    *,
    state: dict | None = None,
    store=None,
    runtime_theme: str | None = None,
    persisted_theme: str | None = None,
    identity: dict | None = None,
    config=None,
) -> dict:
    resolved_config = config or load_config(
        app_path=getattr(program_ir, "app_path", None),
        root=getattr(program_ir, "project_root", None),
    )
    resolved_store = resolve_store(store, config=resolved_config)
    resolved_identity = identity or resolve_identity(
        resolved_config,
        getattr(program_ir, "identity", None),
        mode=ValidationMode.STATIC,
    )
    return build_manifest(
        program_ir,
        state=state or {},
        store=resolved_store,
        runtime_theme=runtime_theme,
        persisted_theme=persisted_theme,
        identity=resolved_identity,
        mode=ValidationMode.STATIC,
    )


def build_ui_contract_payload(
    program_ir,
    *,
    state: dict | None = None,
    store=None,
    runtime_theme: str | None = None,
    persisted_theme: str | None = None,
    identity: dict | None = None,
    config=None,
) -> dict:
    manifest = build_contract_manifest(
        program_ir,
        state=state,
        store=store,
        runtime_theme=runtime_theme,
        persisted_theme=persisted_theme,
        identity=identity,
        config=config,
    )
    return {
        "ui": build_ui_export(manifest),
        "actions": build_actions_export(manifest),
        "schema": build_schema_export(program_ir, manifest),
    }


__all__ = ["build_contract_manifest", "build_ui_contract_payload"]
