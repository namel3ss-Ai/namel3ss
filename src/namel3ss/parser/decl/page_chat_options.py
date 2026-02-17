from __future__ import annotations

from dataclasses import dataclass, field

from namel3ss.errors.base import Namel3ssError

_ALLOWED_CHAT_STYLES = {"bubbles", "plain"}
_ALLOWED_CHAT_ACTIONS = {"copy", "expand", "view_sources"}
_ALLOWED_COMPOSER_SEND_STYLES = {"icon", "text"}
_DEFAULT_COMPOSER_PLACEHOLDER = "Ask about your documents... use #project or @document"


@dataclass
class ChatOptions:
    style: str = "bubbles"
    show_avatars: bool = False
    group_messages: bool = True
    actions: list[str] = field(default_factory=list)
    streaming: bool = False
    attachments: bool = False
    composer_placeholder: str = _DEFAULT_COMPOSER_PLACEHOLDER
    composer_send_style: str = "icon"
    composer_attach_upload: str | None = None


def parse_chat_option_line(
    parser,
    options: ChatOptions,
    seen: set[str],
    *,
    allow_pattern_params: bool = False,
) -> bool:
    del allow_pattern_params
    tok = parser._current()
    if tok.type != "IDENT":
        return False
    name = str(tok.value)
    if name == "style":
        _ensure_not_duplicate(name, seen, tok.line, tok.column)
        parser._advance()
        parser._expect("IS", "Expected 'is' after style")
        value_tok = parser._current()
        if value_tok.type not in {"IDENT", "STRING"}:
            raise Namel3ssError("Chat style must be bubbles or plain.", line=value_tok.line, column=value_tok.column)
        parser._advance()
        value = str(value_tok.value).strip().lower()
        if value not in _ALLOWED_CHAT_STYLES:
            raise Namel3ssError("Chat style must be bubbles or plain.", line=value_tok.line, column=value_tok.column)
        options.style = value
        parser._match("NEWLINE")
        return True
    if name == "show_avatars":
        _ensure_not_duplicate(name, seen, tok.line, tok.column)
        parser._advance()
        parser._expect("IS", "Expected 'is' after show_avatars")
        options.show_avatars = _parse_boolean_literal(parser, message="show_avatars must be true or false")
        parser._match("NEWLINE")
        return True
    if name == "group_messages":
        _ensure_not_duplicate(name, seen, tok.line, tok.column)
        parser._advance()
        parser._expect("IS", "Expected 'is' after group_messages")
        options.group_messages = _parse_boolean_literal(parser, message="group_messages must be true or false")
        parser._match("NEWLINE")
        return True
    if name == "streaming":
        _ensure_not_duplicate(name, seen, tok.line, tok.column)
        parser._advance()
        parser._expect("IS", "Expected 'is' after streaming")
        options.streaming = _parse_boolean_literal(parser, message="streaming must be true or false")
        parser._match("NEWLINE")
        return True
    if name == "attachments":
        _ensure_not_duplicate(name, seen, tok.line, tok.column)
        parser._advance()
        _expect_is_or_are(parser, "Expected 'is' or 'are' after attachments")
        options.attachments = _parse_boolean_literal(parser, message="attachments must be true or false")
        parser._match("NEWLINE")
        return True
    if name == "actions":
        _ensure_not_duplicate(name, seen, tok.line, tok.column)
        parser._advance()
        _expect_is_or_are(parser, "Expected 'is' or 'are' after actions")
        options.actions = _parse_action_list(parser)
        parser._match("NEWLINE")
        return True
    if name == "composer_placeholder":
        _ensure_not_duplicate(name, seen, tok.line, tok.column)
        parser._advance()
        parser._expect("IS", "Expected 'is' after composer_placeholder")
        options.composer_placeholder = _parse_required_text(parser, message="composer_placeholder must be text.")
        parser._match("NEWLINE")
        return True
    if name == "composer_send_style":
        _ensure_not_duplicate(name, seen, tok.line, tok.column)
        parser._advance()
        parser._expect("IS", "Expected 'is' after composer_send_style")
        options.composer_send_style = _parse_choice(
            parser,
            allowed=_ALLOWED_COMPOSER_SEND_STYLES,
            message="composer_send_style must be icon or text.",
        )
        parser._match("NEWLINE")
        return True
    if name == "composer_attach_upload":
        _ensure_not_duplicate(name, seen, tok.line, tok.column)
        parser._advance()
        parser._expect("IS", "Expected 'is' after composer_attach_upload")
        options.composer_attach_upload = _parse_required_text(
            parser,
            message="composer_attach_upload must be text.",
        )
        parser._match("NEWLINE")
        return True
    return False


def _ensure_not_duplicate(name: str, seen: set[str], line: int | None, column: int | None) -> None:
    if name in seen:
        raise Namel3ssError(f"Chat option '{name}' is declared more than once.", line=line, column=column)
    seen.add(name)


def _parse_boolean_literal(parser, *, message: str) -> bool:
    tok = parser._current()
    if tok.type != "BOOLEAN":
        raise Namel3ssError(message, line=tok.line, column=tok.column)
    parser._advance()
    return bool(tok.value)


def _expect_is_or_are(parser, message: str) -> None:
    if parser._match("IS"):
        return
    tok = parser._current()
    if tok.type == "IDENT" and tok.value == "are":
        parser._advance()
        return
    raise Namel3ssError(message, line=tok.line, column=tok.column)


def _parse_action_list(parser) -> list[str]:
    start = parser._current()
    parser._expect("LBRACKET", "Expected '[' after actions")
    actions: list[str] = []
    seen: set[str] = set()
    if parser._match("RBRACKET"):
        return []
    while True:
        tok = parser._current()
        if tok.type not in {"IDENT", "STRING"}:
            raise Namel3ssError("Chat actions must be text names.", line=tok.line, column=tok.column)
        parser._advance()
        value = str(tok.value).strip().lower()
        if value not in _ALLOWED_CHAT_ACTIONS:
            allowed = ", ".join(sorted(_ALLOWED_CHAT_ACTIONS))
            raise Namel3ssError(f"Unknown chat action '{value}'. Expected one of: {allowed}.", line=tok.line, column=tok.column)
        if value not in seen:
            seen.add(value)
            actions.append(value)
        if parser._match("RBRACKET"):
            break
        parser._expect("COMMA", "Expected ',' between chat actions")
    end = parser._current()
    if end.type not in {"NEWLINE", "DEDENT", "COLON"}:
        extra = parser._current()
        raise Namel3ssError(
            "Chat actions must end at the line boundary.",
            line=extra.line or start.line,
            column=extra.column or start.column,
        )
    return actions


def _parse_required_text(parser, *, message: str) -> str:
    tok = parser._current()
    if tok.type not in {"STRING", "IDENT"}:
        raise Namel3ssError(message, line=tok.line, column=tok.column)
    parser._advance()
    value = str(tok.value).strip()
    if not value:
        raise Namel3ssError(message, line=tok.line, column=tok.column)
    return value


def _parse_choice(parser, *, allowed: set[str], message: str) -> str:
    tok = parser._current()
    if tok.type not in {"IDENT", "STRING", "TEXT"} and not tok.type.startswith("TYPE_"):
        raise Namel3ssError(message, line=tok.line, column=tok.column)
    parser._advance()
    value = str(tok.value).strip().lower()
    if value not in allowed:
        raise Namel3ssError(message, line=tok.line, column=tok.column)
    return value


__all__ = ["ChatOptions", "parse_chat_option_line"]
