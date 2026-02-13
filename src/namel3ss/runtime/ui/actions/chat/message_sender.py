from __future__ import annotations

from typing import Optional

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.memory.api import MemoryManager
from namel3ss.runtime.storage.base import Storage
from namel3ss.runtime.ui.actions.chat.flow_action import handle_call_flow_action
from namel3ss.runtime.ui.state.chat_shell import (
    append_chat_user_message,
    ensure_chat_shell_state,
    select_chat_models,
)
from namel3ss.ui.manifest.display_mode import DISPLAY_MODE_STUDIO


def handle_chat_message_send_action(
    program_ir,
    action: dict,
    action_id: str,
    payload: dict,
    state: dict,
    store: Storage,
    runtime_theme: Optional[str],
    memory_manager: MemoryManager | None = None,
    preference_store=None,
    preference_key: str | None = None,
    allow_theme_override: bool | None = None,
    config: AppConfig | None = None,
    identity: dict | None = None,
    auth_context: object | None = None,
    session: dict | None = None,
    secret_values: list[str] | None = None,
    source: str | None = None,
    raise_on_error: bool = True,
    ui_mode: str = DISPLAY_MODE_STUDIO,
    diagnostics_enabled: bool = False,
) -> tuple[dict, Exception | None]:
    ensure_chat_shell_state(state)
    message = _parse_message(payload, state=state)
    _hydrate_composer_state(state, payload)
    append_chat_user_message(state, message)
    state["chat"]["composer_state"]["draft"] = ""
    flow_payload = dict(payload)
    flow_payload.setdefault("message", message)
    model_ids = _resolve_fanout_model_ids(payload, state=state)
    if len(model_ids) > 1:
        return _run_model_fanout(
            program_ir,
            action=action,
            action_id=action_id,
            flow_payload=flow_payload,
            state=state,
            store=store,
            runtime_theme=runtime_theme,
            model_ids=model_ids,
            memory_manager=memory_manager,
            preference_store=preference_store,
            preference_key=preference_key,
            allow_theme_override=allow_theme_override,
            config=config,
            identity=identity,
            auth_context=auth_context,
            session=session,
            secret_values=secret_values,
            source=source,
            raise_on_error=raise_on_error,
            ui_mode=ui_mode,
            diagnostics_enabled=diagnostics_enabled,
        )
    model_id = model_ids[0] if model_ids else None
    return _run_flow_action(
        program_ir,
        action=action,
        action_id=action_id,
        payload=_flow_payload_for_model(flow_payload, model_id=model_id, index=0, count=1),
        state=state,
        store=store,
        runtime_theme=runtime_theme,
        memory_manager=memory_manager,
        preference_store=preference_store,
        preference_key=preference_key,
        allow_theme_override=allow_theme_override,
        config=config,
        identity=identity,
        auth_context=auth_context,
        session=session,
        secret_values=secret_values,
        source=source,
        raise_on_error=raise_on_error,
        ui_mode=ui_mode,
        diagnostics_enabled=diagnostics_enabled,
    )


def _run_flow_action(
    program_ir,
    *,
    action: dict,
    action_id: str,
    payload: dict,
    state: dict,
    store: Storage,
    runtime_theme: Optional[str],
    memory_manager: MemoryManager | None = None,
    preference_store=None,
    preference_key: str | None = None,
    allow_theme_override: bool | None = None,
    config: AppConfig | None = None,
    identity: dict | None = None,
    auth_context: object | None = None,
    session: dict | None = None,
    secret_values: list[str] | None = None,
    source: str | None = None,
    raise_on_error: bool = True,
    ui_mode: str = DISPLAY_MODE_STUDIO,
    diagnostics_enabled: bool = False,
) -> tuple[dict, Exception | None]:
    return handle_call_flow_action(
        program_ir,
        action,
        action_id,
        payload,
        state,
        store,
        runtime_theme,
        memory_manager=memory_manager,
        preference_store=preference_store,
        preference_key=preference_key,
        allow_theme_override=allow_theme_override,
        config=config,
        identity=identity,
        auth_context=auth_context,
        session=session,
        secret_values=secret_values,
        source=source,
        raise_on_error=raise_on_error,
        ui_mode=ui_mode,
        diagnostics_enabled=diagnostics_enabled,
    )


def _run_model_fanout(
    program_ir,
    *,
    action: dict,
    action_id: str,
    flow_payload: dict,
    state: dict,
    store: Storage,
    runtime_theme: Optional[str],
    model_ids: list[str],
    memory_manager: MemoryManager | None = None,
    preference_store=None,
    preference_key: str | None = None,
    allow_theme_override: bool | None = None,
    config: AppConfig | None = None,
    identity: dict | None = None,
    auth_context: object | None = None,
    session: dict | None = None,
    secret_values: list[str] | None = None,
    source: str | None = None,
    raise_on_error: bool = True,
    ui_mode: str = DISPLAY_MODE_STUDIO,
    diagnostics_enabled: bool = False,
) -> tuple[dict, Exception | None]:
    ordered_model_ids = sorted(_normalize_text_list(model_ids))
    if len(ordered_model_ids) <= 1:
        model_id = ordered_model_ids[0] if ordered_model_ids else None
        return _run_flow_action(
            program_ir,
            action=action,
            action_id=action_id,
            payload=_flow_payload_for_model(flow_payload, model_id=model_id, index=0, count=1),
            state=state,
            store=store,
            runtime_theme=runtime_theme,
            memory_manager=memory_manager,
            preference_store=preference_store,
            preference_key=preference_key,
            allow_theme_override=allow_theme_override,
            config=config,
            identity=identity,
            auth_context=auth_context,
            session=session,
            secret_values=secret_values,
            source=source,
            raise_on_error=raise_on_error,
            ui_mode=ui_mode,
            diagnostics_enabled=diagnostics_enabled,
        )
    chat_state = ensure_chat_shell_state(state)
    previous_model_ids = _normalize_text_list(list(chat_state.get("selected_model_ids") or []))
    runs: list[dict] = []
    last_response: dict | None = None
    last_error: Exception | None = None
    try:
        for index, model_id in enumerate(ordered_model_ids):
            select_chat_models(state, [model_id])
            response, action_error = _run_flow_action(
                program_ir,
                action=action,
                action_id=action_id,
                payload=_flow_payload_for_model(
                    flow_payload,
                    model_id=model_id,
                    index=index,
                    count=len(ordered_model_ids),
                ),
                state=state,
                store=store,
                runtime_theme=runtime_theme,
                memory_manager=memory_manager,
                preference_store=preference_store,
                preference_key=preference_key,
                allow_theme_override=allow_theme_override,
                config=config,
                identity=identity,
                auth_context=auth_context,
                session=session,
                secret_values=secret_values,
                source=source,
                raise_on_error=raise_on_error,
                ui_mode=ui_mode,
                diagnostics_enabled=diagnostics_enabled,
            )
            last_response = response
            last_error = action_error
            runs.append(_fanout_run_payload(model_id=model_id, index=index, error=action_error))
            if action_error is not None:
                break
    finally:
        _restore_selected_models(state, previous_model_ids)
    if last_response is None:
        raise Namel3ssError("Chat fanout execution produced no run response.")
    _attach_fanout_result(last_response, model_ids=ordered_model_ids, runs=runs)
    return last_response, last_error


def _parse_message(payload: dict, *, state: dict) -> str:
    if not isinstance(payload, dict):
        raise Namel3ssError("Chat message payload must be an object.")
    message = payload.get("message")
    if isinstance(message, str) and message.strip():
        return message.strip()
    content = payload.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    draft = ((state.get("chat") or {}).get("composer_state") or {}).get("draft")
    if isinstance(draft, str) and draft.strip():
        return draft.strip()
    raise Namel3ssError("Chat message payload requires message text.")


def _hydrate_composer_state(state: dict, payload: dict) -> None:
    composer_state = state["chat"]["composer_state"]
    attachments = payload.get("attachments")
    if isinstance(attachments, list):
        composer_state["attachments"] = _normalize_text_list(attachments)
    tools = payload.get("tools")
    if isinstance(tools, list):
        composer_state["tools"] = _normalize_text_list(tools)
    if "web_search" in payload:
        composer_state["web_search"] = bool(payload.get("web_search"))


def _resolve_fanout_model_ids(payload: dict, *, state: dict) -> list[str]:
    model_ids = _payload_model_ids(payload)
    if model_ids:
        return sorted(model_ids)
    chat = ensure_chat_shell_state(state)
    selected_model_ids = _normalize_text_list(list(chat.get("selected_model_ids") or []))
    if selected_model_ids:
        return sorted(selected_model_ids)
    active_models = _normalize_text_list(list(chat.get("active_models") or []))
    return sorted(active_models)


def _payload_model_ids(payload: dict) -> list[str]:
    if not isinstance(payload, dict):
        return []
    value = payload.get("model_ids")
    if value is None:
        value = payload.get("active")
    if value is None:
        value = payload.get("model_id")
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if not isinstance(value, list):
        raise Namel3ssError("Chat message payload model_ids must be text or a list of text ids.")
    return _normalize_text_list(value)


def _flow_payload_for_model(base_payload: dict, *, model_id: str | None, index: int, count: int) -> dict:
    payload = dict(base_payload)
    if model_id:
        payload["model_id"] = model_id
        payload["model_ids"] = [model_id]
    payload["fanout_index"] = index + 1
    payload["fanout_count"] = max(1, int(count))
    return payload


def _restore_selected_models(state: dict, model_ids: list[str]) -> None:
    if model_ids:
        select_chat_models(state, model_ids)
        return
    chat = ensure_chat_shell_state(state)
    chat["selected_model_ids"] = []
    chat["active_models"] = []


def _fanout_run_payload(*, model_id: str, index: int, error: Exception | None) -> dict:
    payload = {
        "index": index + 1,
        "model_id": model_id,
        "ok": error is None,
    }
    if error is not None:
        payload["error"] = str(error)
    return payload


def _attach_fanout_result(response: dict, *, model_ids: list[str], runs: list[dict]) -> None:
    completed = bool(runs) and len(runs) == len(model_ids) and all(bool(entry.get("ok")) for entry in runs)
    fanout = {
        "completed": completed,
        "enabled": True,
        "model_count": len(model_ids),
        "models": list(model_ids),
        "runs": list(runs),
    }
    current_result = response.get("result")
    if isinstance(current_result, dict):
        result_payload = dict(current_result)
    else:
        result_payload = {}
        if current_result is not None:
            result_payload["output"] = current_result
    result_payload["fanout"] = fanout
    response["result"] = result_payload


def _normalize_text_list(value: list[object]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for entry in value:
        if not isinstance(entry, str):
            continue
        text = entry.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


__all__ = ["handle_chat_message_send_action"]
