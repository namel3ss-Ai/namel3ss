from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.theme.colors import validate_palette_name, validate_token_name
from namel3ss.theme.model import ThemeDefinition
from namel3ss.ui.presets import validate_ui_preset
from namel3ss.ui.settings import validate_ui_value


_AXES = ("density", "motion", "shape", "surface")


def parse_theme_decl(parser) -> ThemeDefinition:
    tok = parser._advance()
    parser._expect("COLON", "Expected ':' after theme")
    parser._expect("NEWLINE", "Expected newline after theme header")
    parser._expect("INDENT", "Expected indented theme block")

    preset: str | None = None
    brand_palette: dict[str, str] = {}
    tokens: dict[str, str] = {}
    harmonize = False
    allow_low_contrast = False
    axes: dict[str, str] = {}

    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        key_tok = parser._expect("IDENT", "Expected theme field name")
        key = str(key_tok.value)
        if key == "brand_palette":
            _expect_colon_or_is(parser, context="brand_palette")
            block = _parse_theme_mapping_block(parser, key_kind="palette")
            for item_key, item_value in block.items():
                if item_key in brand_palette:
                    raise Namel3ssError(
                        f'Duplicate brand_palette key "{item_key}".',
                        line=key_tok.line,
                        column=key_tok.column,
                    )
                brand_palette[item_key] = item_value
            continue
        if key == "tokens":
            _expect_colon_or_is(parser, context="tokens")
            block = _parse_theme_mapping_block(parser, key_kind="token")
            for item_key, item_value in block.items():
                if item_key in tokens:
                    raise Namel3ssError(
                        f'Duplicate token key "{item_key}".',
                        line=key_tok.line,
                        column=key_tok.column,
                    )
                tokens[item_key] = item_value
            continue
        if key == "preset":
            _expect_colon_or_is(parser, context="preset")
            value, value_line, value_col = _parse_text_scalar(parser, context="preset")
            validate_ui_preset(value, line=value_line, column=value_col)
            preset = value
            parser._match("NEWLINE")
            continue
        if key == "harmonize":
            _expect_colon_or_is(parser, context="harmonize")
            harmonize = _parse_boolean_scalar(parser, context="harmonize")
            parser._match("NEWLINE")
            continue
        if key == "allow_low_contrast":
            _expect_colon_or_is(parser, context="allow_low_contrast")
            allow_low_contrast = _parse_boolean_scalar(parser, context="allow_low_contrast")
            parser._match("NEWLINE")
            continue
        if key in _AXES:
            _expect_colon_or_is(parser, context=key)
            value, value_line, value_col = _parse_text_scalar(parser, context=key)
            validate_ui_value(key, value, line=value_line, column=value_col)
            axes[key] = value
            parser._match("NEWLINE")
            continue
        raise Namel3ssError(
            f'Unknown theme field "{key}".',
            line=key_tok.line,
            column=key_tok.column,
        )

    parser._expect("DEDENT", "Expected end of theme block")
    while parser._match("NEWLINE"):
        continue
    return ThemeDefinition(
        preset=preset,
        brand_palette=brand_palette,
        tokens=tokens,
        harmonize=harmonize,
        allow_low_contrast=allow_low_contrast,
        density=axes.get("density"),
        motion=axes.get("motion"),
        shape=axes.get("shape"),
        surface=axes.get("surface"),
        line=tok.line,
        column=tok.column,
    )


def _parse_theme_mapping_block(parser, *, key_kind: str) -> dict[str, str]:
    parser._expect("NEWLINE", "Expected newline before mapping block")
    parser._expect("INDENT", "Expected indented mapping block")
    mapping: dict[str, str] = {}
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        if key_kind == "palette":
            key = _parse_palette_key(parser)
        else:
            key = _parse_dotted_name_until(parser, stop_tokens={"COLON", "IS"}, context="token name")
        _expect_colon_or_is(parser, context=f"{key_kind} entry")
        value, _, _ = _parse_text_scalar(parser, context=f"{key_kind} value", allow_dotted_ident=True)
        mapping[key] = value
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of mapping block")
    return mapping


def _parse_palette_key(parser) -> str:
    key_tok = parser._expect("IDENT", "Expected brand palette key")
    key = str(key_tok.value)
    validate_palette_name(key, line=key_tok.line, column=key_tok.column)
    return key


def _parse_dotted_name_until(parser, *, stop_tokens: set[str], context: str) -> str:
    first = parser._expect("IDENT", f"Expected {context}")
    parts = [str(first.value)]
    while parser._current().type not in stop_tokens:
        if not parser._match("DOT"):
            tok = parser._current()
            raise Namel3ssError(f"Expected '.' or separator while parsing {context}.", line=tok.line, column=tok.column)
        segment_tok = parser._current()
        if segment_tok.type == "IDENT":
            parser._advance()
            parts.append(str(segment_tok.value))
            continue
        if segment_tok.type == "NUMBER":
            parser._advance()
            parts.append(str(segment_tok.value))
            continue
        raise Namel3ssError(
            f"Expected identifier or number in {context}.",
            line=segment_tok.line,
            column=segment_tok.column,
        )
    value = ".".join(parts)
    validate_token_name(value, line=first.line, column=first.column)
    return value


def _expect_colon_or_is(parser, *, context: str) -> None:
    if parser._match("COLON"):
        return
    parser._expect("IS", f"Expected ':' or 'is' after {context}")


def _parse_text_scalar(
    parser,
    *,
    context: str,
    allow_dotted_ident: bool = False,
) -> tuple[str, int | None, int | None]:
    tok = parser._current()
    if tok.type == "STRING":
        parser._advance()
        return str(tok.value), tok.line, tok.column
    if tok.type == "IDENT":
        if not allow_dotted_ident:
            parser._advance()
            return str(tok.value), tok.line, tok.column
        value = _parse_dotted_name_until(parser, stop_tokens={"NEWLINE", "DEDENT"}, context=context)
        return value, tok.line, tok.column
    raise Namel3ssError(f"Expected {context} value.", line=tok.line, column=tok.column)


def _parse_boolean_scalar(parser, *, context: str) -> bool:
    tok = parser._current()
    if tok.type != "BOOLEAN":
        raise Namel3ssError(f"{context} must be a boolean literal.", line=tok.line, column=tok.column)
    parser._advance()
    return bool(tok.value)


__all__ = ["parse_theme_decl"]

