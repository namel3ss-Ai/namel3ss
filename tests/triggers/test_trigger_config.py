from __future__ import annotations

from pathlib import Path

from namel3ss.triggers import (
    dispatch_trigger_events,
    enqueue_trigger_event,
    list_triggers,
    load_trigger_config,
    load_trigger_events,
    register_trigger,
    save_trigger_config,
)
from tests.conftest import lower_ir_program


def _write_app(tmp_path: Path) -> Path:
    app = tmp_path / "app.ai"
    app.write_text(
        'spec is "1.0"\n\n'
        'flow "welcome_flow":\n'
        '  return "ok"\n',
        encoding="utf-8",
    )
    return app


def test_trigger_config_register_save_and_load_is_deterministic(tmp_path: Path) -> None:
    app = _write_app(tmp_path)
    config = load_trigger_config(app.parent, app)
    assert config == []

    config = register_trigger(
        config,
        trigger_type="webhook",
        name="user_signup",
        pattern="/hooks/signup",
        flow="welcome_flow",
    )
    config = register_trigger(
        config,
        trigger_type="timer",
        name="nightly_cleanup",
        pattern="0 0 * * *",
        flow="welcome_flow",
    )
    out_path = save_trigger_config(app.parent, app, config)
    loaded = load_trigger_config(app.parent, app)

    assert out_path.exists()
    assert list_triggers(loaded) == list_triggers(config)
    assert [row["name"] for row in list_triggers(loaded)] == ["nightly_cleanup", "user_signup"]


def test_trigger_event_queue_is_sorted_and_dispatches(tmp_path: Path) -> None:
    app = _write_app(tmp_path)
    program = lower_ir_program(app.read_text(encoding="utf-8"))

    enqueue_trigger_event(
        app.parent,
        app,
        trigger_type="timer",
        trigger_name="nightly_cleanup",
        pattern="0 0 * * *",
        flow_name="welcome_flow",
        payload={"z": 2, "a": 1},
        step_count=2,
    )
    enqueue_trigger_event(
        app.parent,
        app,
        trigger_type="webhook",
        trigger_name="user_signup",
        pattern="/hooks/signup",
        flow_name="welcome_flow",
        payload={"id": "abc"},
        step_count=1,
    )

    queued = load_trigger_events(app.parent, app)
    assert [event.trigger_name for event in queued] == ["user_signup", "nightly_cleanup"]

    payload = dispatch_trigger_events(program=program, project_root=app.parent, app_path=app)
    assert payload["count"] == 2
    assert payload["ok"] is True
    assert load_trigger_events(app.parent, app) == []
