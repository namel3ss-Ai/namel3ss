from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.parser.decl.type_reference import parse_type_reference


_AI_FLOW_KINDS = {"llm_call", "rag", "classification", "summarise"}


def parse_ai_flow_decl(parser) -> ast.AIFlowDefinition:
    kind_tok = parser._advance()
    kind = str(kind_tok.value)
    if kind not in _AI_FLOW_KINDS:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unknown AI flow type '{kind}'.",
                why="AI flow declarations must use llm_call, rag, classification, or summarise.",
                fix="Use one of the supported AI flow types.",
                example='llm_call "summarise":',
            ),
            line=kind_tok.line,
            column=kind_tok.column,
        )
    name_tok = parser._expect("STRING", "Expected AI flow name string")
    parser._expect("COLON", "Expected ':' after AI flow name")
    parser._expect("NEWLINE", "Expected newline after AI flow header")
    parser._expect("INDENT", "Expected indented AI flow block")

    model = None
    prompt = None
    dataset = None
    output_type = None
    labels = None
    sources = None
    return_expr = None
    seen_return = False

    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if seen_return:
            raise Namel3ssError(
                build_guidance_message(
                    what="Return must be the final line of the AI flow block.",
                    why="AI flow blocks can only end with an optional return expression.",
                    fix="Move the return to the bottom of the block.",
                    example=f'{kind} "{name_tok.value}":\n  model is "gpt-4"\n  prompt is "Summarise."\n  return "ok"',
                ),
                line=tok.line,
                column=tok.column,
            )
        if tok.type == "RETURN":
            parser._advance()
            return_expr = parser._parse_expression()
            seen_return = True
            parser._match("NEWLINE")
            continue
        if tok.type == "MODEL":
            parser._advance()
            _ensure_unique("model", model, tok)
            parser._expect("IS", "Expected 'is' after model")
            value_tok = parser._expect("STRING", "Expected model string")
            model = value_tok.value
            parser._match("NEWLINE")
            continue
        if _match_ident(parser, "model"):
            _ensure_unique("model", model, tok)
            parser._expect("IS", "Expected 'is' after model")
            value_tok = parser._expect("STRING", "Expected model string")
            model = value_tok.value
            parser._match("NEWLINE")
            continue
        if _match_ident(parser, "prompt"):
            _ensure_unique("prompt", prompt, tok)
            parser._expect("IS", "Expected 'is' after prompt")
            value_tok = parser._expect("STRING", "Expected prompt string")
            prompt = value_tok.value
            parser._match("NEWLINE")
            continue
        if _match_ident(parser, "dataset"):
            _ensure_unique("dataset", dataset, tok)
            parser._expect("IS", "Expected 'is' after dataset")
            value_tok = parser._expect("STRING", "Expected dataset string")
            dataset = value_tok.value
            parser._match("NEWLINE")
            continue
        if _match_ident(parser, "output"):
            _ensure_unique("output", output_type, tok)
            parser._expect("IS", "Expected 'is' after output")
            output_type, _, _, _, _ = parse_type_reference(parser)
            parser._match("NEWLINE")
            continue
        if kind == "rag" and _match_ident(parser, "sources"):
            _ensure_unique("sources", sources, tok)
            sources = _parse_value_block(parser, label="sources", allow_strings=False)
            continue
        if kind == "classification" and _match_ident(parser, "labels"):
            _ensure_unique("labels", labels, tok)
            labels = _parse_value_block(parser, label="labels", allow_strings=True)
            continue
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unknown {kind} field '{tok.value}'.",
                why="AI flow blocks only allow model, prompt, dataset, output, and any required list blocks.",
                fix="Remove the line or use a supported field.",
                example=(
                    f'{kind} "example":\n'
                    '  model is "gpt-4"\n'
                    '  prompt is "Summarise the input."\n'
                    '  output is text'
                ),
            ),
            line=tok.line,
            column=tok.column,
        )

    parser._expect("DEDENT", "Expected end of AI flow block")
    while parser._match("NEWLINE"):
        pass

    if model is None:
        raise Namel3ssError("AI flow is missing a model", line=kind_tok.line, column=kind_tok.column)
    if prompt is None:
        raise Namel3ssError("AI flow is missing a prompt", line=kind_tok.line, column=kind_tok.column)
    if kind == "rag" and not sources:
        raise Namel3ssError("RAG flow is missing sources", line=kind_tok.line, column=kind_tok.column)
    if kind == "classification" and not labels:
        raise Namel3ssError("Classification flow is missing labels", line=kind_tok.line, column=kind_tok.column)

    return ast.AIFlowDefinition(
        name=name_tok.value,
        kind=kind,
        model=model,
        prompt=prompt,
        dataset=dataset,
        output_type=output_type,
        labels=labels,
        sources=sources,
        return_expr=return_expr,
        line=kind_tok.line,
        column=kind_tok.column,
    )


def _parse_value_block(parser, *, label: str, allow_strings: bool) -> list[str]:
    header_tok = parser._current()
    parser._expect("COLON", f"Expected ':' after {label}")
    parser._expect("NEWLINE", f"Expected newline after {label}")
    if not parser._match("INDENT"):
        raise Namel3ssError(
            build_guidance_message(
                what=f"{label.title()} block has no entries.",
                why=f"{label.title()} blocks require at least one entry.",
                fix=f"Add one or more entries under {label}.",
                example=f"{label}:\n  example",
            ),
            line=header_tok.line,
            column=header_tok.column,
        )
    values: list[str] = []
    seen: set[str] = set()
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type == "IDENT":
            value = tok.value
            parser._advance()
        elif allow_strings and tok.type == "STRING":
            value = tok.value
            parser._advance()
        else:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"{label.title()} entries must be simple names.",
                    why=f"{label.title()} blocks list one entry per line.",
                    fix="Use a single name per line or quote the value.",
                    example=f"{label}:\n  example",
                ),
                line=tok.line,
                column=tok.column,
            )
        if value in seen:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Duplicate {label} entry '{value}'.",
                    why="Each entry may only appear once.",
                    fix="Remove the duplicate entry.",
                    example=f"{label}:\n  {value}",
                ),
                line=tok.line,
                column=tok.column,
            )
        seen.add(value)
        values.append(value)
        parser._match("NEWLINE")
    parser._expect("DEDENT", f"Expected end of {label} block")
    while parser._match("NEWLINE"):
        pass
    if not values:
        raise Namel3ssError(
            build_guidance_message(
                what=f"{label.title()} block has no entries.",
                why=f"{label.title()} blocks require at least one entry.",
                fix=f"Add one or more entries under {label}.",
                example=f"{label}:\n  example",
            ),
            line=header_tok.line,
            column=header_tok.column,
        )
    return values


def _ensure_unique(field: str, current: object | None, tok) -> None:
    if current is None:
        return
    raise Namel3ssError(
        build_guidance_message(
            what=f"AI flow declares {field} more than once.",
            why="Each field may only be declared once.",
            fix=f"Keep a single {field} entry.",
            example=f'{field} is "..."',
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


__all__ = ["parse_ai_flow_decl"]
