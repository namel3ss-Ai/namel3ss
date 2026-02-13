from pathlib import Path


def test_run_module_exposes_chat_thread_route_helpers() -> None:
    js = Path("src/namel3ss/studio/web/studio/run.js").read_text(encoding="utf-8")
    for expected in [
        'return _requestChatRoute("/api/chat/threads"',
        "function loadChatThread(",
        "function saveChatThread(",
        "run.listChatThreads = listChatThreads",
        "run.loadChatThread = loadChatThread",
        "run.saveChatThread = saveChatThread",
    ]:
        assert expected in js


def test_run_module_supports_chat_thread_sse_stream_callbacks() -> None:
    js = Path("src/namel3ss/studio/web/studio/run.js").read_text(encoding="utf-8")
    for expected in [
        "function _streamChatRoute(",
        "function _parseSseFrame(",
        "_withStreamQuery(path)",
        "event === \"return\"",
        "opts.onStreamEvent",
    ]:
        assert expected in js


def test_scope_selector_uses_chat_thread_routes_with_action_fallback() -> None:
    js = Path("src/namel3ss/studio/web/ui_renderer_rag.js").read_text(encoding="utf-8")
    for expected in [
        'const isChatThreadSelector = actionType === "chat.thread.select"',
        "run.listChatThreads",
        "run.saveChatThread",
        "run.loadChatThread",
        "dispatchSelectorAction(",
        "runThreadRouteSelection(",
        "scopeOptionLabel(",
        "scopeOptionTooltip(",
        "message_count",
        "last_message_id",
    ]:
        assert expected in js
