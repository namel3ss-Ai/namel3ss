from __future__ import annotations

from pathlib import Path
from typing import Mapping

from namel3ss.config.model import AppConfig
from namel3ss.runtime.capabilities.contract_fields import attach_capability_contract_fields
from namel3ss.runtime.audit.audit_bundle import write_audit_bundle
from namel3ss.runtime.audit.audit_policy import (
    AUDIT_MODE_FORBIDDEN,
    audit_writing_enabled,
    audit_writing_required,
    build_audit_policy_status,
    resolve_audit_mode,
)
from namel3ss.runtime.audit.run_artifact import build_run_artifact
from namel3ss.runtime.errors.classification import build_runtime_error
from namel3ss.runtime.persistence.contract_fields import attach_persistence_contract_fields
from namel3ss.secrets import collect_secret_values


def attach_audit_artifacts(
    response: dict,
    *,
    program_ir: object | None,
    config: AppConfig | None,
    action_id: str | None = None,
    flow_name: str | None = None,
    input_payload: Mapping[str, object] | None = None,
    state_snapshot: Mapping[str, object] | None = None,
    source: str | None = None,
    endpoint: str = "/api/action",
) -> dict:
    if not isinstance(response, dict):
        return response
    response = attach_persistence_contract_fields(response, program_ir=program_ir, config=config)
    response = attach_capability_contract_fields(response, program_ir=program_ir, config=config)
    mode = resolve_audit_mode(config)
    if mode == AUDIT_MODE_FORBIDDEN:
        response.pop("run_artifact", None)
        response.pop("audit_bundle", None)
        response["audit_policy_status"] = build_audit_policy_status(mode, attempted=False, written=False)
        return response
    project_root = _project_root(program_ir)
    app_path = _app_path(program_ir)
    provider_name = _provider_name(config)
    model_name = _model_name(config)
    secret_values = collect_secret_values(config)
    artifact = build_run_artifact(
        response=response,
        app_path=app_path,
        source=source or _source_from_path(app_path),
        flow_name=flow_name,
        action_id=action_id,
        input_payload=input_payload,
        state_snapshot=state_snapshot,
        provider_name=provider_name,
        model_name=model_name,
        project_root=project_root,
        secret_values=secret_values,
    )
    response["run_artifact"] = artifact
    attempted = bool(project_root and audit_writing_enabled(mode))
    written = False
    error_text = ""
    if attempted:
        try:
            bundle = write_audit_bundle(project_root, artifact)
            response["audit_bundle"] = bundle
            written = True
        except Exception as exc:  # pragma: no cover - defensive
            error_text = str(exc) or "Audit bundle write failed."
    elif audit_writing_required(mode):
        error_text = "Audit policy is required but project root is unavailable."
    if error_text and audit_writing_required(mode):
        return _attach_required_error(
            response,
            endpoint=endpoint,
            error_text=error_text,
            mode=mode,
            attempted=attempted,
        )
    response["audit_policy_status"] = build_audit_policy_status(
        mode,
        attempted=attempted,
        written=written,
        error=error_text or None,
    )
    return response


def _attach_required_error(
    response: dict,
    *,
    endpoint: str,
    error_text: str,
    mode: str,
    attempted: bool,
) -> dict:
    response["ok"] = False
    response["error"] = {"message": "Audit artifact write failed."}
    diagnostic = build_runtime_error(
        "policy_denied",
        message="Audit policy requires writing run artifacts, but the audit bundle could not be written.",
        hint="Ensure .namel3ss/audit is writable or set audit.mode to optional.",
        origin="policy",
        stable_code="runtime.policy_denied.audit_required",
    )
    response["runtime_error"] = diagnostic
    response["runtime_errors"] = [diagnostic]
    response["audit_policy_status"] = build_audit_policy_status(
        mode,
        attempted=attempted,
        written=False,
        error=error_text,
    )
    response.pop("audit_bundle", None)
    return response


def _project_root(program_ir: object | None) -> str | None:
    value = getattr(program_ir, "project_root", None)
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return None


def _app_path(program_ir: object | None) -> str | None:
    value = getattr(program_ir, "app_path", None)
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return None


def _provider_name(config: AppConfig | None) -> str | None:
    if config is None:
        return None
    provider = getattr(getattr(config, "answer", None), "provider", None)
    if isinstance(provider, str):
        text = provider.strip()
        return text or None
    return None


def _model_name(config: AppConfig | None) -> str | None:
    if config is None:
        return None
    model = getattr(getattr(config, "answer", None), "model", None)
    if isinstance(model, str):
        text = model.strip()
        return text or None
    return None


def _source_from_path(app_path: str | None) -> str | None:
    if not app_path:
        return None
    try:
        return Path(app_path).read_text(encoding="utf-8")
    except OSError:
        return None


__all__ = ["attach_audit_artifacts"]
