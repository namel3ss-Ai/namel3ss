from __future__ import annotations

from namel3ss.config.loader import load_config
from namel3ss.runtime.capabilities.contract_fields import attach_capability_contract_fields
from namel3ss.runtime.identity.context import resolve_identity
from namel3ss.runtime.persistence.contract_fields import attach_persistence_contract_fields
from namel3ss.runtime.storage.factory import resolve_store
from namel3ss.ui.export.actions import build_actions_export
from namel3ss.ui.export.schema import build_schema_export
from namel3ss.ui.export.ui import build_ui_export
from namel3ss.ui.manifest import build_manifest
from namel3ss.ui.manifest.display_mode import DISPLAY_MODE_STUDIO
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
    ui_mode: str = DISPLAY_MODE_STUDIO,
    diagnostics_enabled: bool = True,
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
        config=resolved_config,
        state=state or {},
        store=resolved_store,
        runtime_theme=runtime_theme,
        persisted_theme=persisted_theme,
        identity=resolved_identity,
        mode=ValidationMode.STATIC,
        display_mode=ui_mode,
        diagnostics_enabled=diagnostics_enabled,
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
    ui_mode: str = DISPLAY_MODE_STUDIO,
    diagnostics_enabled: bool = True,
) -> dict:
    resolved_config = config or load_config(
        app_path=getattr(program_ir, "app_path", None),
        root=getattr(program_ir, "project_root", None),
    )
    manifest = build_contract_manifest(
        program_ir,
        state=state,
        store=store,
        runtime_theme=runtime_theme,
        persisted_theme=persisted_theme,
        identity=identity,
        config=resolved_config,
        ui_mode=ui_mode,
        diagnostics_enabled=diagnostics_enabled,
    )
    payload = {
        "ui": build_ui_export(manifest),
        "actions": build_actions_export(manifest),
        "schema": build_schema_export(program_ir, manifest),
    }
    enriched = attach_capability_contract_fields(
        {"ui": payload["ui"]},
        program_ir=program_ir,
        config=resolved_config,
    )
    enriched = attach_persistence_contract_fields(
        enriched,
        program_ir=program_ir,
        config=resolved_config,
    )
    ui_payload = enriched.get("ui") if isinstance(enriched.get("ui"), dict) else payload["ui"]
    payload["ui"] = ui_payload
    payload["persistence_backend"] = enriched.get("persistence_backend")
    payload["state_schema_version"] = enriched.get("state_schema_version")
    payload["migration_status"] = enriched.get("migration_status")
    payload["capabilities_enabled"] = enriched.get("capabilities_enabled")
    payload["capability_versions"] = enriched.get("capability_versions")
    return payload


__all__ = ["build_contract_manifest", "build_ui_contract_payload"]
