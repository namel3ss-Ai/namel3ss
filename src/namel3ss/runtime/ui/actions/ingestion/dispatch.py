from __future__ import annotations

from namel3ss.runtime.ui.actions.build.dispatch_context import ActionDispatchContext
from namel3ss.runtime.ui.actions.build.dispatch_contract import ActionHandler
from namel3ss.runtime.ui.actions.ingestion.review import handle_ingestion_review_action
from namel3ss.runtime.ui.actions.ingestion.run import handle_ingestion_run_action
from namel3ss.runtime.ui.actions.ingestion.skip import handle_ingestion_skip_action


def _run_ingestion_run(ctx: ActionDispatchContext) -> tuple[dict, Exception | None]:
    response = handle_ingestion_run_action(
        ctx.program_ir,
        action_id=ctx.action_id,
        payload=ctx.payload,
        state=ctx.state,
        store=ctx.store,
        runtime_theme=ctx.runtime_theme,
        config=ctx.config,
        identity=ctx.identity,
        auth_context=ctx.auth_context,
        secret_values=ctx.secret_values,
    )
    return response, None


def _run_ingestion_review(ctx: ActionDispatchContext) -> tuple[dict, Exception | None]:
    response = handle_ingestion_review_action(
        ctx.program_ir,
        action_id=ctx.action_id,
        payload=ctx.payload,
        state=ctx.state,
        store=ctx.store,
        runtime_theme=ctx.runtime_theme,
        config=ctx.config,
        identity=ctx.identity,
        auth_context=ctx.auth_context,
        secret_values=ctx.secret_values,
    )
    return response, None


def _run_ingestion_skip(ctx: ActionDispatchContext) -> tuple[dict, Exception | None]:
    response = handle_ingestion_skip_action(
        ctx.program_ir,
        action_id=ctx.action_id,
        payload=ctx.payload,
        state=ctx.state,
        store=ctx.store,
        runtime_theme=ctx.runtime_theme,
        config=ctx.config,
        identity=ctx.identity,
        auth_context=ctx.auth_context,
        secret_values=ctx.secret_values,
    )
    return response, None


ACTION_HANDLERS: dict[str, ActionHandler] = {
    "ingestion_review": _run_ingestion_review,
    "ingestion_run": _run_ingestion_run,
    "ingestion_skip": _run_ingestion_skip,
}


__all__ = ["ACTION_HANDLERS"]
