from __future__ import annotations

"""
Story parsing is isolated here to keep the shared page_items module small and focused.
"""

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.decl.page_common import (
    _parse_debug_only_clause,
    _is_visibility_rule_start,
    _parse_string_value,
    _parse_visibility_clause,
    _parse_show_when_clause,
    _parse_visibility_rule_line,
    _validate_visibility_combo,
)
from namel3ss.parser.decl.page_media import parse_image_role_block

_ALLOWED_STEP_FIELDS = ("text", "icon", "image", "tone", "requires", "next")


def parse_story_block(parser, *, allow_pattern_params: bool = False) -> ast.StoryItem:
    story_tok = parser._current()
    parser._advance()
    title = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="story title")
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    parser._expect("COLON", "Expected ':' after story title")
    parser._expect("NEWLINE", "Expected newline after story header")
    parser._expect("INDENT", "Expected indented story body")
    steps: list[ast.StoryStep] = []
    visibility_rule: ast.VisibilityRule | None = None
    mode: str | None = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if _is_visibility_rule_start(parser):
            if visibility_rule is not None:
                raise Namel3ssError("Visibility blocks may only declare one only-when rule.", line=tok.line, column=tok.column)
            visibility_rule = _parse_visibility_rule_line(parser, allow_pattern_params=allow_pattern_params)
            parser._match("NEWLINE")
            continue
        if tok.type == "STRING":
            if mode == "advanced":
                raise Namel3ssError("Story cannot mix quoted steps with step blocks", line=tok.line, column=tok.column)
            mode = "simple"
            parser._advance()
            steps.append(ast.StoryStep(title=tok.value, line=tok.line, column=tok.column))
            parser._match("NEWLINE")
            continue
        if tok.type == "IDENT" and tok.value == "step":
            if mode == "simple":
                raise Namel3ssError("Story cannot mix quoted steps with step blocks", line=tok.line, column=tok.column)
            mode = "advanced"
            steps.append(_parse_step_block(parser, allow_pattern_params=allow_pattern_params))
            continue
        raise Namel3ssError("Story may only contain quoted step titles or 'step' blocks", line=tok.line, column=tok.column)
    parser._expect("DEDENT", "Expected end of story block")
    if not steps:
        raise Namel3ssError("Story has no steps", line=story_tok.line, column=story_tok.column)
    _validate_visibility_combo(visibility, visibility_rule, line=story_tok.line, column=story_tok.column)
    return ast.StoryItem(
        title=title,
        steps=steps,
        visibility=visibility,
        visibility_rule=visibility_rule,
        show_when=show_when,
        debug_only=debug_only,
        line=story_tok.line,
        column=story_tok.column,
    )


def _parse_step_block(parser, *, allow_pattern_params: bool) -> ast.StoryStep:
    step_tok = parser._current()
    parser._advance()
    title = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="step title")
    parser._expect("COLON", "Expected ':' after step title")
    parser._expect("NEWLINE", "Expected newline after step header")
    parser._expect("INDENT", "Expected indented step body")
    text = None
    icon = None
    image = None
    image_role = None
    tone = None
    requires = None
    next_step = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        field_tok = parser._current()
        field = field_tok.value
        if field not in _ALLOWED_STEP_FIELDS:
            raise Namel3ssError(
                "Story step may only declare text, icon, image, tone, requires, or next",
                line=field_tok.line,
                column=field_tok.column,
            )
        parser._advance()
        parser._expect("IS", f"Expected 'is' after {field}")
        if field == "text":
            if text is not None:
                raise Namel3ssError("Step text is already declared", line=field_tok.line, column=field_tok.column)
            text = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="step text")
        elif field == "icon":
            if icon is not None:
                raise Namel3ssError("Step icon is already declared", line=field_tok.line, column=field_tok.column)
            if parser._current().type == "STRING":
                icon_tok = parser._advance()
                icon = icon_tok.value
            else:
                icon_tok = parser._expect("IDENT", "Expected icon name")
                icon = icon_tok.value
        elif field == "image":
            if image is not None:
                raise Namel3ssError("Step image is already declared", line=field_tok.line, column=field_tok.column)
            image = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="image")
            if parser._match("COLON"):
                image_role = parse_image_role_block(parser, line=field_tok.line, column=field_tok.column)
                continue
        elif field == "tone":
            if tone is not None:
                raise Namel3ssError("Step tone is already declared", line=field_tok.line, column=field_tok.column)
            tone = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="tone")
        elif field == "requires":
            if requires is not None:
                raise Namel3ssError("Step requires is already declared", line=field_tok.line, column=field_tok.column)
            requires = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="requires")
        elif field == "next":
            if next_step is not None:
                raise Namel3ssError("Step next is already declared", line=field_tok.line, column=field_tok.column)
            next_step = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="next step title")
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of step body")
    return ast.StoryStep(
        title=title,
        text=text,
        icon=icon,
        image=image,
        image_role=image_role,
        tone=tone,
        requires=requires,
        next=next_step,
        line=step_tok.line,
        column=step_tok.column,
    )


__all__ = ["parse_story_block"]
