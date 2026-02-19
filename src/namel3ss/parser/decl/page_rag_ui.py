from __future__ import annotations

from dataclasses import replace

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.decl.page_common import (
    _parse_reference_name_value,
    _parse_state_path_value,
)
from namel3ss.ui.theme_tokens import UI_THEME_ALLOWED_VALUES, UI_THEME_TOKEN_ORDER, normalize_ui_theme_token_value

_RAG_UI_BASES = ("assistant", "evidence", "research")
_RAG_UI_FEATURES = ("conversation", "evidence", "research_tools")
_RAG_UI_DEFAULT_FEATURES = {
    "assistant": ("conversation",),
    "evidence": ("conversation", "evidence"),
    "research": ("conversation", "evidence", "research_tools"),
}
_RAG_UI_SLOTS = ("header", "sidebar", "drawer", "chat", "composer")
_RAG_UI_BIND_KEYS = {
    "messages",
    "on_send",
    "citations",
    "thinking",
    "threads",
    "active_thread",
    "models",
    "active_models",
    "suggestions",
    "composer_state",
    "drawer_open",
    "source_preview",
    "sources",
    "upload",
    "ingest_flow",
    "scope_options",
    "scope_active",
    "trust",
    "toggle_sources",
    "toggle_drawer",
    "toggle_settings",
}


def parse_rag_ui_block(parser) -> ast.RagUIBlock:
    rag_tok = parser._advance()
    parser._expect("COLON", "Expected ':' after rag_ui")
    parser._expect("NEWLINE", "Expected newline after rag_ui header")
    parser._expect("INDENT", "Expected indented rag_ui block")
    base: str | None = None
    features: list[str] = []
    binds: ast.RagUIBindings | None = None
    slots: dict[str, list[ast.PageItem]] = {}
    theme_tokens: dict[str, str] = {}
    theme_line: int | None = None
    theme_column: int | None = None
    seen_keys: set[str] = set()
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type != "IDENT":
            raise Namel3ssError("Expected rag_ui entry", line=tok.line, column=tok.column)
        key = str(tok.value)
        if key in UI_THEME_ALLOWED_VALUES:
            _parse_theme_override_line(parser, theme_tokens)
            if theme_line is None:
                theme_line = tok.line
                theme_column = tok.column
            parser._match("NEWLINE")
            continue
        if key == "base":
            if key in seen_keys:
                raise Namel3ssError("rag_ui base is already declared.", line=tok.line, column=tok.column)
            seen_keys.add(key)
            base = _parse_base_line(parser)
            parser._match("NEWLINE")
            continue
        if key == "features":
            if key in seen_keys:
                raise Namel3ssError("rag_ui features are already declared.", line=tok.line, column=tok.column)
            seen_keys.add(key)
            features = _parse_features_line(parser)
            parser._match("NEWLINE")
            continue
        if key == "binds":
            if key in seen_keys:
                raise Namel3ssError("rag_ui binds are already declared.", line=tok.line, column=tok.column)
            seen_keys.add(key)
            binds = _parse_binds_block(parser)
            continue
        if key == "slots":
            if key in seen_keys:
                raise Namel3ssError("rag_ui slots are already declared.", line=tok.line, column=tok.column)
            seen_keys.add(key)
            slots = _parse_slots_block(parser)
            continue
        raise Namel3ssError(f"Unknown rag_ui entry '{key}'.", line=tok.line, column=tok.column)
    parser._expect("DEDENT", "Expected end of rag_ui block")
    resolved_base = _resolve_base(base, line=rag_tok.line, column=rag_tok.column)
    resolved_features = _resolve_features(features, resolved_base, line=rag_tok.line, column=rag_tok.column)
    _validate_required_binds(binds, resolved_features, line=rag_tok.line, column=rag_tok.column)
    theme_overrides = None
    if theme_tokens:
        theme_overrides = ast.ThemeTokens(
            size=theme_tokens.get("size"),
            radius=theme_tokens.get("radius"),
            density=theme_tokens.get("density"),
            font=theme_tokens.get("font"),
            color_scheme=theme_tokens.get("color_scheme"),
            line=theme_line,
            column=theme_column,
        )
    return ast.RagUIBlock(
        base=resolved_base,
        features=list(resolved_features),
        bindings=binds,
        slots=slots,
        theme_overrides=theme_overrides,
        line=rag_tok.line,
        column=rag_tok.column,
    )


def _parse_base_line(parser) -> str:
    parser._advance()
    if not parser._match("IS"):
        parser._expect("IS", "Expected 'is' after base")
    value_tok = parser._current()
    if value_tok.type not in {"STRING", "IDENT"}:
        raise Namel3ssError("Expected base style value.", line=value_tok.line, column=value_tok.column)
    parser._advance()
    value = str(value_tok.value).strip().lower()
    if value not in _RAG_UI_BASES:
        allowed = ", ".join(_RAG_UI_BASES)
        raise Namel3ssError(f"Unknown rag_ui base '{value}'. Allowed values: {allowed}.", line=value_tok.line, column=value_tok.column)
    return value


def _parse_features_line(parser) -> list[str]:
    parser._advance()
    if not parser._match("COLON"):
        parser._expect("IS", "Expected ':' or 'is' after features")
    values: list[str] = []
    seen: set[str] = set()
    while True:
        tok = parser._current()
        if tok.type not in {"IDENT", "STRING"}:
            if not values:
                raise Namel3ssError("rag_ui features require at least one entry.", line=tok.line, column=tok.column)
            break
        parser._advance()
        value = str(tok.value).strip().lower()
        if value not in _RAG_UI_FEATURES:
            allowed = ", ".join(_RAG_UI_FEATURES)
            raise Namel3ssError(f"Unknown rag_ui feature '{value}'. Allowed values: {allowed}.", line=tok.line, column=tok.column)
        if value in seen:
            raise Namel3ssError(f"rag_ui feature '{value}' is duplicated.", line=tok.line, column=tok.column)
        seen.add(value)
        values.append(value)
        if not parser._match("COMMA"):
            break
    return values


def _parse_binds_block(parser) -> ast.RagUIBindings:
    binds_tok = parser._advance()
    parser._expect("COLON", "Expected ':' after binds")
    parser._expect("NEWLINE", "Expected newline after binds")
    parser._expect("INDENT", "Expected indented binds block")
    seen: set[str] = set()
    bindings = ast.RagUIBindings(line=binds_tok.line, column=binds_tok.column)
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type != "IDENT":
            raise Namel3ssError("Expected bind name", line=tok.line, column=tok.column)
        key = str(tok.value)
        if key not in _RAG_UI_BIND_KEYS:
            allowed = ", ".join(sorted(_RAG_UI_BIND_KEYS))
            raise Namel3ssError(f"Unknown rag_ui bind '{key}'. Allowed binds: {allowed}.", line=tok.line, column=tok.column)
        if key in seen:
            raise Namel3ssError(f"rag_ui bind '{key}' is already declared.", line=tok.line, column=tok.column)
        seen.add(key)
        parser._advance()
        if key in {"messages", "citations", "sources", "threads", "models", "suggestions"}:
            _expect_from_keyword(parser, f"{key} bind must use: {key} from is state.<path>")
            parser._expect("IS", "Expected 'is' after from")
            value = _parse_state_path_value(parser, allow_pattern_params=False)
            bindings = replace(bindings, **{key: value})
            parser._match("NEWLINE")
            continue
        if key in {
            "thinking",
            "drawer_open",
            "trust",
            "scope_options",
            "scope_active",
            "active_thread",
            "active_models",
            "composer_state",
        }:
            _consume_when_or_is(parser, key)
            value = _parse_state_path_value(parser, allow_pattern_params=False)
            bindings = replace(bindings, **{key: value})
            parser._match("NEWLINE")
            continue
        if key in {"on_send", "ingest_flow", "toggle_sources", "toggle_drawer", "toggle_settings"}:
            parser._expect("CALLS", "Expected 'calls' for flow binding")
            parser._expect("FLOW", "Expected 'flow' after calls")
            flow_name = _parse_reference_name_value(parser, allow_pattern_params=False, context="flow")
            attr = _flow_bind_attr(key)
            bindings = replace(bindings, **{attr: flow_name})
            parser._match("NEWLINE")
            continue
        if key == "upload":
            parser._expect("IS", "Expected 'is' after upload")
            name = _parse_upload_name(parser)
            bindings = replace(bindings, upload=name)
            parser._match("NEWLINE")
            continue
        if key == "source_preview":
            _expect_from_keyword(parser, "source_preview bind must use: source_preview from is state.<path> or text")
            parser._expect("IS", "Expected 'is' after from")
            value = _parse_source_reference(parser)
            bindings = replace(bindings, source_preview=value)
            parser._match("NEWLINE")
            continue
        raise Namel3ssError(f"Unsupported rag_ui bind '{key}'.", line=tok.line, column=tok.column)
    parser._expect("DEDENT", "Expected end of binds block")
    if not seen:
        raise Namel3ssError("rag_ui binds block has no entries.", line=binds_tok.line, column=binds_tok.column)
    return bindings


def _parse_slots_block(parser) -> dict[str, list[ast.PageItem]]:
    from namel3ss.parser.decl.page_items import parse_page_item

    slots_tok = parser._advance()
    parser._expect("COLON", "Expected ':' after slots")
    parser._expect("NEWLINE", "Expected newline after slots")
    parser._expect("INDENT", "Expected indented slots block")
    slots: dict[str, list[ast.PageItem]] = {}
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        slot_tok = parser._expect("IDENT", "Expected slot name")
        slot_name = str(slot_tok.value)
        if slot_name not in _RAG_UI_SLOTS:
            allowed = ", ".join(_RAG_UI_SLOTS)
            raise Namel3ssError(f"Unknown rag_ui slot '{slot_name}'. Allowed slots: {allowed}.", line=slot_tok.line, column=slot_tok.column)
        if slot_name in slots:
            raise Namel3ssError(f"rag_ui slot '{slot_name}' is already declared.", line=slot_tok.line, column=slot_tok.column)
        parser._expect("COLON", "Expected ':' after slot name")
        parser._expect("NEWLINE", f"Expected newline after {slot_name}")
        if not parser._match("INDENT"):
            slots[slot_name] = []
            continue
        items: list[ast.PageItem] = []
        while parser._current().type != "DEDENT":
            if parser._match("NEWLINE"):
                continue
            parsed = parse_page_item(parser, allow_tabs=True, allow_overlays=True)
            if isinstance(parsed, list):
                items.extend(parsed)
            else:
                items.append(parsed)
        parser._expect("DEDENT", f"Expected end of {slot_name} slot")
        slots[slot_name] = items
    parser._expect("DEDENT", "Expected end of slots block")
    if not slots:
        raise Namel3ssError("rag_ui slots block has no entries.", line=slots_tok.line, column=slots_tok.column)
    return slots


def _parse_theme_override_line(parser, theme_tokens: dict[str, str]) -> None:
    tok = parser._current()
    if tok.type != "IDENT":
        raise Namel3ssError("Expected theme token name.", line=tok.line, column=tok.column)
    name = str(tok.value)
    if name not in UI_THEME_ALLOWED_VALUES:
        allowed = ", ".join(UI_THEME_TOKEN_ORDER)
        raise Namel3ssError(f"Unknown token '{name}'. Allowed tokens: {allowed}.", line=tok.line, column=tok.column)
    if name in theme_tokens:
        raise Namel3ssError(f"duplicate definition for {name}.", line=tok.line, column=tok.column)
    parser._advance()
    if not parser._match("COLON"):
        parser._expect("IS", f"Expected 'is' after {name}")
    value_tok = parser._current()
    if value_tok.type not in {"STRING", "IDENT"}:
        raise Namel3ssError(f"Expected {name} token value.", line=value_tok.line, column=value_tok.column)
    parser._advance()
    theme_tokens[name] = normalize_ui_theme_token_value(
        name,
        str(value_tok.value),
        line=value_tok.line,
        column=value_tok.column,
    )


def _resolve_base(base: str | None, *, line: int | None, column: int | None) -> str:
    if base is None:
        return "assistant"
    value = base.strip().lower()
    if value not in _RAG_UI_BASES:
        allowed = ", ".join(_RAG_UI_BASES)
        raise Namel3ssError(f"Unknown rag_ui base '{value}'. Allowed values: {allowed}.", line=line, column=column)
    return value


def _resolve_features(features: list[str], base: str, *, line: int | None, column: int | None) -> tuple[str, ...]:
    if not features:
        return tuple(_RAG_UI_DEFAULT_FEATURES.get(base, ()))
    resolved: list[str] = []
    seen: set[str] = set()
    for value in features:
        normalized = str(value).strip().lower()
        if normalized not in _RAG_UI_FEATURES:
            allowed = ", ".join(_RAG_UI_FEATURES)
            raise Namel3ssError(f"Unknown rag_ui feature '{normalized}'. Allowed values: {allowed}.", line=line, column=column)
        if normalized in seen:
            raise Namel3ssError(f"rag_ui feature '{normalized}' is duplicated.", line=line, column=column)
        seen.add(normalized)
        resolved.append(normalized)
    return tuple(resolved)


def _validate_required_binds(
    binds: ast.RagUIBindings | None,
    features: tuple[str, ...],
    *,
    line: int | None,
    column: int | None,
) -> None:
    if binds is None:
        return
    _validate_shell_binds(binds, line=line, column=column)


def _validate_shell_binds(
    binds: ast.RagUIBindings,
    *,
    line: int | None,
    column: int | None,
) -> None:
    if binds.threads is not None and binds.active_thread is None:
        raise Namel3ssError(
            "rag_ui threads requires active_thread when is state.<path>.",
            line=line,
            column=column,
        )
    if binds.active_thread is not None and binds.threads is None:
        raise Namel3ssError(
            "rag_ui active_thread requires threads from is state.<path>.",
            line=line,
            column=column,
        )
    if binds.models is not None and binds.active_models is None:
        raise Namel3ssError(
            "rag_ui models requires active_models when is state.<path>.",
            line=line,
            column=column,
        )
    if binds.active_models is not None and binds.models is None:
        raise Namel3ssError(
            "rag_ui active_models requires models from is state.<path>.",
            line=line,
            column=column,
        )


def _expect_from_keyword(parser, message: str) -> None:
    tok = parser._current()
    if tok.type != "IDENT" or tok.value != "from":
        raise Namel3ssError(message, line=tok.line, column=tok.column)
    parser._advance()


def _consume_when_or_is(parser, key: str) -> None:
    if parser._match("WHEN"):
        parser._match("IS")
        return
    if parser._match("IS"):
        return
    tok = parser._current()
    raise Namel3ssError(f"{key} bind must use: {key} when is state.<path>", line=tok.line, column=tok.column)


def _parse_upload_name(parser) -> str:
    tok = parser._current()
    if tok.type in {"IDENT", "STRING"}:
        parser._advance()
        return str(tok.value)
    raise Namel3ssError("Upload bind requires a name value.", line=tok.line, column=tok.column)


def _parse_source_reference(parser) -> ast.StatePath | ast.Literal:
    tok = parser._current()
    if tok.type == "STATE":
        return _parse_state_path_value(parser, allow_pattern_params=False)
    if tok.type in {"STRING", "IDENT"}:
        parser._advance()
        return ast.Literal(value=str(tok.value), line=tok.line, column=tok.column)
    raise Namel3ssError(
        "source_preview bind requires state.<path> or text.",
        line=tok.line,
        column=tok.column,
    )


def _flow_bind_attr(key: str) -> str:
    mapping = {
        "on_send": "on_send",
        "ingest_flow": "ingest_flow",
        "toggle_sources": "toggle_sources_flow",
        "toggle_drawer": "toggle_drawer_flow",
        "toggle_settings": "toggle_settings_flow",
    }
    return mapping[key]


__all__ = ["parse_rag_ui_block"]
