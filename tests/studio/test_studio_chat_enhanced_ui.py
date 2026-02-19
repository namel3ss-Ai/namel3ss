from pathlib import Path


def test_chat_renderer_includes_enhanced_message_features() -> None:
    js = Path("src/namel3ss/studio/web/ui_renderer_chat.js").read_text(encoding="utf-8")
    for expected in [
        "ui-chat-style-${style}",
        "ui-chat-avatar",
        "group_start",
        "ui-chat-message-actions",
        "ui-chat-message-action-icon-plain",
        "renderMessageAttachments",
        "renderStreamingContent",
        "view_sources",
    ]:
        assert expected in js


def test_chat_css_includes_bubbles_grouping_and_streaming_styles() -> None:
    css = Path("src/namel3ss/studio/web/studio_ui.css").read_text(encoding="utf-8")
    css += Path("src/namel3ss/studio/web/styles/chat.css").read_text(encoding="utf-8")
    for selector in [
        ".ui-chat-bubble",
        ".ui-chat-avatar",
        ".ui-chat-message.group-continue",
        ".ui-chat-message.is-streaming",
        ".ui-chat-message-actions",
        ".ui-chat-message-action-icon-plain",
        ".ui-chat-attachments",
        ".ui-chat-thinking.user-visible",
    ]:
        assert selector in css
