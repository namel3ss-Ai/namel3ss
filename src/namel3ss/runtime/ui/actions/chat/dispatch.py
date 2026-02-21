from __future__ import annotations

from namel3ss.observability.enablement import resolve_observability_context
from namel3ss.runtime.ui.actions.build.dispatch_context import ActionDispatchContext
from namel3ss.runtime.ui.actions.build.dispatch_contract import ActionHandler
from namel3ss.runtime.ui.actions.chat.branch_selector import handle_chat_branch_select_action
from namel3ss.runtime.ui.actions.chat.flow_action import handle_call_flow_action
from namel3ss.runtime.ui.actions.chat.form_submit import handle_submit_form_action
from namel3ss.runtime.ui.actions.chat.message_regenerator import handle_chat_message_regenerate_action
from namel3ss.runtime.ui.actions.chat.message_sender import handle_chat_message_send_action
from namel3ss.runtime.ui.actions.chat.model_selector import handle_chat_model_select_action
from namel3ss.runtime.ui.actions.chat.stream_cancel import handle_chat_stream_cancel_action
from namel3ss.runtime.ui.actions.chat.thread_creator import handle_chat_thread_new_action
from namel3ss.runtime.ui.actions.chat.thread_selector import handle_chat_thread_select_action
from namel3ss.runtime.ui.contracts.action_kind import (
    CHAT_BRANCH_SELECT,
    CHAT_MESSAGE_REGENERATE,
    CHAT_MESSAGE_SEND,
    CHAT_MODEL_SELECT,
    CHAT_STREAM_CANCEL,
    CHAT_THREAD_NEW,
    CHAT_THREAD_SELECT,
)


def _run_call_flow(ctx: ActionDispatchContext) -> tuple[dict, Exception | None]:
    response, action_error = handle_call_flow_action(
        ctx.program_ir,
        ctx.action,
        ctx.action_id,
        ctx.payload,
        ctx.state,
        ctx.store,
        ctx.runtime_theme,
        memory_manager=ctx.memory_manager,
        preference_store=ctx.preference_store,
        preference_key=ctx.preference_key,
        allow_theme_override=ctx.allow_theme_override,
        config=ctx.config,
        identity=ctx.identity,
        auth_context=ctx.auth_context,
        session=ctx.session,
        secret_values=ctx.secret_values,
        source=ctx.source,
        raise_on_error=ctx.raise_on_error,
        ui_mode=ctx.ui_mode,
        diagnostics_enabled=ctx.diagnostics_enabled,
    )
    if action_error and ctx.raise_on_error:
        raise action_error
    return response, action_error


def _run_submit_form(ctx: ActionDispatchContext) -> tuple[dict, Exception | None]:
    obs, owns_obs = resolve_observability_context(
        None,
        project_root=getattr(ctx.program_ir, "project_root", None),
        app_path=getattr(ctx.program_ir, "app_path", None),
        config=ctx.config,
    )
    span_id = None
    span_status = "ok"
    if obs and owns_obs:
        obs.start_session()
    if obs:
        span_id = obs.start_span(
            None,
            name=f"action:{ctx.action_id}",
            kind="action",
            details={"action_id": ctx.action_id, "type": "submit_form"},
            timing_name="action",
            timing_labels={"action": ctx.action_id, "type": "submit_form"},
        )
    try:
        response = handle_submit_form_action(
            ctx.program_ir,
            ctx.action,
            ctx.action_id,
            ctx.payload,
            ctx.state,
            ctx.store,
            ctx.manifest,
            ctx.runtime_theme,
            config=ctx.config,
            identity=ctx.identity,
            secret_values=ctx.secret_values,
            source=ctx.source,
            ui_mode=ctx.ui_mode,
            diagnostics_enabled=ctx.diagnostics_enabled,
        )
    except Exception:
        span_status = "error"
        raise
    finally:
        if obs and span_id:
            obs.end_span(None, span_id, status=span_status)
        if obs and owns_obs:
            obs.flush()
    return response, None


def _run_chat_model_select(ctx: ActionDispatchContext) -> tuple[dict, Exception | None]:
    response = handle_chat_model_select_action(
        ctx.program_ir,
        action=ctx.action,
        action_id=ctx.action_id,
        payload=ctx.payload,
        state=ctx.state,
        store=ctx.store,
        runtime_theme=ctx.runtime_theme,
        config=ctx.config,
        identity=ctx.identity,
        auth_context=ctx.auth_context,
        secret_values=ctx.secret_values,
        ui_mode=ctx.ui_mode,
        diagnostics_enabled=ctx.diagnostics_enabled,
    )
    return response, None


def _run_chat_thread_select(ctx: ActionDispatchContext) -> tuple[dict, Exception | None]:
    response = handle_chat_thread_select_action(
        ctx.program_ir,
        action=ctx.action,
        action_id=ctx.action_id,
        payload=ctx.payload,
        state=ctx.state,
        store=ctx.store,
        runtime_theme=ctx.runtime_theme,
        config=ctx.config,
        identity=ctx.identity,
        auth_context=ctx.auth_context,
        secret_values=ctx.secret_values,
        ui_mode=ctx.ui_mode,
        diagnostics_enabled=ctx.diagnostics_enabled,
    )
    return response, None


def _run_chat_thread_new(ctx: ActionDispatchContext) -> tuple[dict, Exception | None]:
    response = handle_chat_thread_new_action(
        ctx.program_ir,
        action=ctx.action,
        action_id=ctx.action_id,
        payload=ctx.payload,
        state=ctx.state,
        store=ctx.store,
        runtime_theme=ctx.runtime_theme,
        config=ctx.config,
        identity=ctx.identity,
        auth_context=ctx.auth_context,
        secret_values=ctx.secret_values,
        ui_mode=ctx.ui_mode,
        diagnostics_enabled=ctx.diagnostics_enabled,
    )
    return response, None


def _run_chat_message_send(ctx: ActionDispatchContext) -> tuple[dict, Exception | None]:
    response, action_error = handle_chat_message_send_action(
        ctx.program_ir,
        action=ctx.action,
        action_id=ctx.action_id,
        payload=ctx.payload,
        state=ctx.state,
        store=ctx.store,
        runtime_theme=ctx.runtime_theme,
        memory_manager=ctx.memory_manager,
        preference_store=ctx.preference_store,
        preference_key=ctx.preference_key,
        allow_theme_override=ctx.allow_theme_override,
        config=ctx.config,
        identity=ctx.identity,
        auth_context=ctx.auth_context,
        session=ctx.session,
        secret_values=ctx.secret_values,
        source=ctx.source,
        raise_on_error=ctx.raise_on_error,
        ui_mode=ctx.ui_mode,
        diagnostics_enabled=ctx.diagnostics_enabled,
    )
    if action_error and ctx.raise_on_error:
        raise action_error
    return response, action_error


def _run_chat_message_regenerate(ctx: ActionDispatchContext) -> tuple[dict, Exception | None]:
    response = handle_chat_message_regenerate_action(
        ctx.program_ir,
        action=ctx.action,
        action_id=ctx.action_id,
        payload=ctx.payload,
        state=ctx.state,
        store=ctx.store,
        runtime_theme=ctx.runtime_theme,
        config=ctx.config,
        identity=ctx.identity,
        auth_context=ctx.auth_context,
        secret_values=ctx.secret_values,
        ui_mode=ctx.ui_mode,
        diagnostics_enabled=ctx.diagnostics_enabled,
    )
    return response, None


def _run_chat_branch_select(ctx: ActionDispatchContext) -> tuple[dict, Exception | None]:
    response = handle_chat_branch_select_action(
        ctx.program_ir,
        action=ctx.action,
        action_id=ctx.action_id,
        payload=ctx.payload,
        state=ctx.state,
        store=ctx.store,
        runtime_theme=ctx.runtime_theme,
        config=ctx.config,
        identity=ctx.identity,
        auth_context=ctx.auth_context,
        secret_values=ctx.secret_values,
        ui_mode=ctx.ui_mode,
        diagnostics_enabled=ctx.diagnostics_enabled,
    )
    return response, None


def _run_chat_stream_cancel(ctx: ActionDispatchContext) -> tuple[dict, Exception | None]:
    response = handle_chat_stream_cancel_action(
        ctx.program_ir,
        action=ctx.action,
        action_id=ctx.action_id,
        payload=ctx.payload,
        state=ctx.state,
        store=ctx.store,
        runtime_theme=ctx.runtime_theme,
        config=ctx.config,
        identity=ctx.identity,
        auth_context=ctx.auth_context,
        secret_values=ctx.secret_values,
        ui_mode=ctx.ui_mode,
        diagnostics_enabled=ctx.diagnostics_enabled,
    )
    return response, None


ACTION_HANDLERS: dict[str, ActionHandler] = {
    "call_flow": _run_call_flow,
    CHAT_BRANCH_SELECT: _run_chat_branch_select,
    CHAT_MESSAGE_REGENERATE: _run_chat_message_regenerate,
    CHAT_MESSAGE_SEND: _run_chat_message_send,
    CHAT_MODEL_SELECT: _run_chat_model_select,
    CHAT_STREAM_CANCEL: _run_chat_stream_cancel,
    CHAT_THREAD_NEW: _run_chat_thread_new,
    CHAT_THREAD_SELECT: _run_chat_thread_select,
    "chat_model_select": _run_chat_model_select,
    "chat_thread_select": _run_chat_thread_select,
    "submit_form": _run_submit_form,
}


__all__ = ["ACTION_HANDLERS"]
