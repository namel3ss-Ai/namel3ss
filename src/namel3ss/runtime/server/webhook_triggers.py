from __future__ import annotations

from collections.abc import Callable

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_payload
from namel3ss.triggers import enqueue_trigger_event, load_trigger_config


def handle_webhook_trigger_post(
    *,
    path: str,
    program,
    read_json_body: Callable[[], dict | None],
    respond_json: Callable[..., None],
) -> bool:
    if program is None:
        return False
    project_root = getattr(program, "project_root", None)
    app_path = getattr(program, "app_path", None)
    try:
        triggers = load_trigger_config(project_root, app_path)
    except Namel3ssError:
        return False
    except Exception:
        return False
    matches = [
        trigger
        for trigger in triggers
        if trigger.type == "webhook" and str(trigger.pattern or "").strip() == path
    ]
    if not matches:
        return False
    payload = read_json_body()
    if payload is None:
        respond_json(build_error_payload("Invalid webhook JSON body", kind="engine"), status=400)
        return True
    ordered = sorted(matches, key=lambda item: (item.name, item.flow))
    for trigger in ordered:
        enqueue_trigger_event(
            project_root,
            app_path,
            trigger_type="webhook",
            trigger_name=trigger.name,
            pattern=trigger.pattern,
            flow_name=trigger.flow,
            payload=payload,
        )
    respond_json(
        {
            "ok": True,
            "trigger_type": "webhook",
            "enqueued": [item.name for item in ordered],
            "count": len(ordered),
        },
        status=200,
        sort_keys=True,
    )
    return True


__all__ = ["handle_webhook_trigger_post"]

