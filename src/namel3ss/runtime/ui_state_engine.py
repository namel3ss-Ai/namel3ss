from __future__ import annotations

import json
from copy import deepcopy


_SCOPE_ORDER = ("ephemeral", "session", "persistent")


class UIStateEngineError(RuntimeError):
    pass


def storage_keys(app_id: str) -> dict[str, str]:
    stable_app_id = _stable_app_id(app_id)
    prefix = f"namel3ss.ui_state.{stable_app_id}"
    return {
        "session": f"{prefix}.session",
        "persistent": f"{prefix}.persistent",
    }


def build_declared_defaults(declaration: object | None) -> dict:
    if declaration is None:
        return {}
    ui_defaults: dict[str, object] = {}
    for _scope, field in _iter_declaration_fields(declaration):
        key = str(getattr(field, "key", "") or "")
        if not key:
            continue
        if hasattr(field, "default_value"):
            ui_defaults[key] = deepcopy(getattr(field, "default_value"))
            continue
        type_name = str(getattr(field, "type_name", "") or "")
        ui_defaults[key] = default_value_for_type(type_name)
    if not ui_defaults:
        return {}
    return {"ui": ui_defaults}


def restore_state(
    *,
    base_state: dict | None,
    declaration: object | None,
    app_id: str,
    session_store: object | None,
    persistent_store: object | None,
) -> tuple[dict, dict[str, str]]:
    state = deepcopy(base_state) if isinstance(base_state, dict) else {}
    if declaration is None:
        return state, {}
    defaults = build_declared_defaults(declaration)
    _merge_missing(state, defaults)
    value_source: dict[str, str] = {}
    session_payload = _read_scope_payload(
        store=session_store,
        storage_key=storage_keys(app_id)["session"],
        scope="session",
    )
    persistent_payload = _read_scope_payload(
        store=persistent_store,
        storage_key=storage_keys(app_id)["persistent"],
        scope="persistent",
    )
    _apply_scope_payload(
        state=state,
        declaration=declaration,
        scope="session",
        payload=session_payload,
        value_source=value_source,
    )
    _apply_scope_payload(
        state=state,
        declaration=declaration,
        scope="persistent",
        payload=persistent_payload,
        value_source=value_source,
    )
    _fill_default_sources(declaration, value_source)
    return state, value_source


def persist_state(
    *,
    state: dict | None,
    declaration: object | None,
    app_id: str,
    session_store: object | None,
    persistent_store: object | None,
) -> None:
    if declaration is None:
        return
    state_ui = state.get("ui") if isinstance(state, dict) else None
    values = state_ui if isinstance(state_ui, dict) else {}
    keys = storage_keys(app_id)
    session_payload = _scope_payload_for_store(declaration, "session", values)
    persistent_payload = _scope_payload_for_store(declaration, "persistent", values)
    _write_scope_payload(
        store=session_store,
        storage_key=keys["session"],
        payload=session_payload,
    )
    _write_scope_payload(
        store=persistent_store,
        storage_key=keys["persistent"],
        payload=persistent_payload,
    )


def default_value_for_type(type_name: str) -> object:
    normalized = str(type_name or "").strip()
    if "|" in normalized:
        normalized = normalized.split("|", 1)[0].strip()
    lowered = normalized.lower()
    if lowered in {"text", "string"}:
        return ""
    if lowered in {"number", "int", "integer"}:
        return 0
    if lowered in {"boolean", "bool"}:
        return False
    if lowered == "null":
        return None
    if lowered.startswith("list<") or lowered == "list":
        return []
    if lowered.startswith("map<") or lowered in {"map", "json"}:
        return {}
    return {}


def _scope_payload_for_store(declaration: object, scope: str, values: dict) -> dict:
    payload: dict[str, object] = {}
    for declared_scope, field in _iter_declaration_fields(declaration):
        if declared_scope != scope:
            continue
        key = str(getattr(field, "key", "") or "")
        if not key:
            continue
        if key in values:
            payload[key] = deepcopy(values[key])
            continue
        payload[key] = deepcopy(getattr(field, "default_value", default_value_for_type(str(getattr(field, "type_name", "") or ""))))
    return payload


def _apply_scope_payload(
    *,
    state: dict,
    declaration: object,
    scope: str,
    payload: dict,
    value_source: dict[str, str],
) -> None:
    if not payload:
        return
    ui = state.setdefault("ui", {})
    if not isinstance(ui, dict):
        ui = {}
        state["ui"] = ui
    for declared_scope, field in _iter_declaration_fields(declaration):
        if declared_scope != scope:
            continue
        key = str(getattr(field, "key", "") or "")
        if not key:
            continue
        if key not in payload:
            continue
        ui[key] = deepcopy(payload[key])
        value_source[f"ui.{key}"] = "restored"


def _fill_default_sources(declaration: object, value_source: dict[str, str]) -> None:
    for _scope, field in _iter_declaration_fields(declaration):
        key = str(getattr(field, "key", "") or "")
        if not key:
            continue
        path = f"ui.{key}"
        if path not in value_source:
            value_source[path] = "default"


def _read_scope_payload(*, store: object | None, storage_key: str, scope: str) -> dict:
    raw = _store_get(store, storage_key)
    if raw is None:
        return {}
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    if not isinstance(raw, str):
        raise UIStateEngineError(f"Stored ui_state payload for scope '{scope}' is not valid text.")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as err:
        raise UIStateEngineError(
            f"Stored ui_state payload for scope '{scope}' is invalid JSON."
        ) from err
    if not isinstance(payload, dict):
        raise UIStateEngineError(
            f"Stored ui_state payload for scope '{scope}' must be a JSON object."
        )
    return payload


def _write_scope_payload(*, store: object | None, storage_key: str, payload: dict) -> None:
    if store is None:
        return
    if not payload:
        _store_delete(store, storage_key)
        return
    text = _serialize_payload(payload)
    _store_set(store, storage_key, text)


def _serialize_payload(payload: dict) -> str:
    try:
        return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    except (TypeError, ValueError) as err:
        raise UIStateEngineError(
            "Unable to persist ui_state values. Values must be JSON-serializable."
        ) from err


def _iter_declaration_fields(declaration: object) -> list[tuple[str, object]]:
    ordered: list[tuple[str, object]] = []
    for scope in _SCOPE_ORDER:
        fields = getattr(declaration, scope, None) or []
        for field in fields:
            ordered.append((scope, field))
    return ordered


def _stable_app_id(app_id: str) -> str:
    text = str(app_id or "").strip().lower()
    if not text:
        return "app"
    safe_chars: list[str] = []
    for ch in text:
        if ch.isalnum() or ch in {"_", "-", "."}:
            safe_chars.append(ch)
            continue
        safe_chars.append("_")
    return "".join(safe_chars)


def _merge_missing(target: dict, defaults: dict) -> None:
    for key in sorted(defaults.keys(), key=str):
        value = defaults[key]
        if isinstance(value, dict):
            current = target.get(key)
            if isinstance(current, dict):
                _merge_missing(current, value)
                continue
            target[key] = deepcopy(value)
            continue
        if key not in target:
            target[key] = deepcopy(value)


def _store_get(store: object | None, key: str) -> object | None:
    if store is None:
        return None
    getter = getattr(store, "get", None)
    if callable(getter):
        try:
            return getter(key)
        except TypeError:
            return getter(key, None)
    if isinstance(store, dict):
        return store.get(key)
    try:
        return store[key]  # type: ignore[index]
    except Exception:
        return None


def _store_set(store: object | None, key: str, value: str) -> None:
    if store is None:
        return
    setter = getattr(store, "__setitem__", None)
    if callable(setter):
        setter(key, value)
        return
    putter = getattr(store, "set", None)
    if callable(putter):
        putter(key, value)


def _store_delete(store: object | None, key: str) -> None:
    if store is None:
        return
    deleter = getattr(store, "__delitem__", None)
    if callable(deleter):
        try:
            deleter(key)
            return
        except Exception:
            pass
    popper = getattr(store, "pop", None)
    if callable(popper):
        try:
            popper(key)
        except TypeError:
            popper(key, None)
        return
    setter = getattr(store, "set", None)
    if callable(setter):
        setter(key, "")


__all__ = [
    "UIStateEngineError",
    "build_declared_defaults",
    "default_value_for_type",
    "persist_state",
    "restore_state",
    "storage_keys",
]
