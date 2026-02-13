from pathlib import Path


def test_chat_renderer_wires_graph_controls() -> None:
    js = Path("src/namel3ss/studio/web/ui_renderer_chat.js").read_text(encoding="utf-8")
    for expected in [
        'normalizeControlAction(payload.branch_action_id, "chat.branch.select")',
        'normalizeControlAction(payload.regenerate_action_id, "chat.message.regenerate")',
        'normalizeControlAction(payload.stream_cancel_action_id, "chat.stream.cancel")',
        "renderMessageGraphControls(",
        "Switch branch",
        "Regenerate",
        "Stop",
        "message_id",
    ]:
        assert expected in js
