from __future__ import annotations

from namel3ss.config.model import AppConfig
from namel3ss.ir import nodes as ir
from namel3ss.runtime.records.inspection import (
    DEFAULT_RECORD_LIMIT,
    build_record_effects,
    build_records_payload,
    collect_record_rows,
)
from namel3ss.runtime.storage.base import Storage


def records_snapshot(program: ir.Program, store: Storage, config: AppConfig | None) -> list[dict]:
    identity = _identity_defaults(config)
    rows, errors = collect_record_rows(program.records, store, identity)
    return build_records_payload(program.records, rows, errors, limit=DEFAULT_RECORD_LIMIT)


def record_rows_snapshot(program: ir.Program, store: Storage, config: AppConfig | None) -> dict[str, list[dict]]:
    identity = _identity_defaults(config)
    rows, _errors = collect_record_rows(program.records, store, identity)
    return rows


def record_data_effects(
    program: ir.Program,
    store: Storage,
    config: AppConfig | None,
    action_id: str,
    response: dict,
    before_rows: dict[str, list[dict]],
) -> dict:
    identity = _identity_defaults(config)
    after_rows, _errors = collect_record_rows(program.records, store, identity)
    effects = build_record_effects(program.records, before_rows, after_rows)
    action_meta = _action_metadata(action_id, response)
    status = "ok" if isinstance(response, dict) and response.get("ok", True) else "error"
    return {"action": action_meta, "status": status, "records": effects}


def _identity_defaults(config: AppConfig | None) -> dict:
    if not config:
        return {}
    identity = getattr(config, "identity", None)
    return dict(identity.defaults) if identity else {}


def _action_metadata(action_id: str, response: dict | None) -> dict:
    meta = {"id": action_id}
    if not isinstance(response, dict):
        return meta
    ui_payload = response.get("ui") if isinstance(response.get("ui"), dict) else {}
    actions = ui_payload.get("actions") if isinstance(ui_payload.get("actions"), dict) else {}
    entry = actions.get(action_id) if isinstance(actions, dict) else None
    if isinstance(entry, dict):
        if entry.get("type"):
            meta["type"] = entry.get("type")
        if entry.get("flow"):
            meta["flow"] = entry.get("flow")
        if entry.get("record"):
            meta["record"] = entry.get("record")
        if entry.get("target"):
            meta["target"] = entry.get("target")
    return meta


__all__ = ["record_data_effects", "record_rows_snapshot", "records_snapshot"]
