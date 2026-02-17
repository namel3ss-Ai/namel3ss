from __future__ import annotations

from namel3ss.runtime.ui.actions.build.dispatch_context import ActionDispatchContext
from namel3ss.runtime.ui.actions.build.dispatch_contract import ActionHandler
from namel3ss.runtime.ui.actions.retrieval.run import handle_retrieval_run_action


def _run_retrieval_run(ctx: ActionDispatchContext) -> tuple[dict, Exception | None]:
    response = handle_retrieval_run_action(
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
        ui_mode=ctx.ui_mode,
        diagnostics_enabled=ctx.diagnostics_enabled,
    )
    return response, None


ACTION_HANDLERS: dict[str, ActionHandler] = {"retrieval_run": _run_retrieval_run}


__all__ = ["ACTION_HANDLERS"]
