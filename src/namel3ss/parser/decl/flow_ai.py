from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def parse_flow_ai_block(parser) -> ast.AIFlowMetadata:
    ai_tok = parser._advance()
    parser._expect("COLON", "Expected ':' after ai")
    parser._expect("NEWLINE", "Expected newline after ai")
    parser._expect("INDENT", "Expected indented ai block")
    model = None
    prompt = None
    prompt_expr = None
    dataset = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        key_tok = parser._current()
        if key_tok.type == "MODEL":
            parser._advance()
            _ensure_unique("model", model, key_tok)
            parser._expect("IS", "Expected 'is' after model")
            value_tok = parser._expect("STRING", "Expected model string")
            model = value_tok.value
            parser._match("NEWLINE")
            continue
        if _match_ident(parser, "model"):
            _ensure_unique("model", model, key_tok)
            parser._expect("IS", "Expected 'is' after model")
            value_tok = parser._expect("STRING", "Expected model string")
            model = value_tok.value
            parser._match("NEWLINE")
            continue
        if _match_ident(parser, "prompt"):
            _ensure_unique("prompt", prompt if prompt_expr is None else object(), key_tok)
            parser._expect("IS", "Expected 'is' after prompt")
            value_expr = parser._parse_expression()
            if isinstance(value_expr, ast.Literal) and isinstance(value_expr.value, str):
                prompt = value_expr.value
                prompt_expr = None
            else:
                prompt = None
                prompt_expr = value_expr
            parser._match("NEWLINE")
            continue
        if _match_ident(parser, "dataset"):
            _ensure_unique("dataset", dataset, key_tok)
            parser._expect("IS", "Expected 'is' after dataset")
            value_tok = parser._expect("STRING", "Expected dataset string")
            dataset = value_tok.value
            parser._match("NEWLINE")
            continue
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unknown ai field '{key_tok.value}'.",
                why="AI blocks only allow model, prompt, and dataset.",
                fix="Remove the line or use a supported field.",
                example=(
                    'ai:\n'
                    '  model is "gpt-4"\n'
                    '  prompt is "Summarise the input."'
                ),
            ),
            line=key_tok.line,
            column=key_tok.column,
        )
    parser._expect("DEDENT", "Expected end of ai block")
    while parser._match("NEWLINE"):
        pass
    if model is None:
        raise Namel3ssError("AI block requires a model", line=ai_tok.line, column=ai_tok.column)
    if prompt is None and prompt_expr is None:
        raise Namel3ssError("AI block requires a prompt", line=ai_tok.line, column=ai_tok.column)
    return ast.AIFlowMetadata(
        model=model,
        prompt=prompt,
        prompt_expr=prompt_expr,
        dataset=dataset,
        line=ai_tok.line,
        column=ai_tok.column,
    )


def _ensure_unique(field: str, current: object | None, tok) -> None:
    if current is None:
        return
    raise Namel3ssError(
        build_guidance_message(
            what=f"AI block declares {field} more than once.",
            why="Each AI field may only be declared once.",
            fix=f"Keep a single {field} entry.",
            example=f"{field} is \"...\"",
        ),
        line=tok.line,
        column=tok.column,
    )


def _match_ident(parser, value: str) -> bool:
    tok = parser._current()
    if tok.type == "IDENT" and tok.value == value:
        parser._advance()
        return True
    return False


__all__ = ["parse_flow_ai_block"]
