from __future__ import annotations
from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.parser.decl.type_reference import parse_type_reference
_AI_FLOW_KINDS = {
    "llm_call",
    "rag",
    "classification",
    "summarise",
    "translate",
    "qa",
    "cot",
    "chain",
}
_KIND_ALIASES = {"classify": "classification"}
def parse_ai_flow_decl(parser) -> ast.AIFlowDefinition:
    kind_tok = parser._advance()
    raw_kind = str(kind_tok.value)
    kind = _normalize_kind(raw_kind)
    if kind not in _AI_FLOW_KINDS:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unknown AI flow type '{raw_kind}'.",
                why="AI flow declarations must use a supported pattern name.",
                fix="Use llm_call, rag, classification, summarise, translate, qa, cot, or chain.",
                example='translate "en_to_fr":',
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
    prompt_expr = None
    dataset = None
    output_type = None
    source_language = None
    target_language = None
    output_fields: list[ast.AIOutputField] | None = None
    labels = None
    sources = None
    chain_steps: list[ast.ChainStep] | None = None
    tests: ast.AIFlowTestConfig | None = None
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
                    fix="Move return to the bottom of the block.",
                    example='qa "answer_question":\n  model is "gpt-4"\n  prompt is "Qn: hello"\n  return "ok"',
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
        if _match_word(parser, "model"):
            _ensure_unique("model", model, tok)
            parser._expect("IS", "Expected 'is' after model")
            value_tok = parser._expect("STRING", "Expected model string")
            model = value_tok.value
            parser._match("NEWLINE")
            continue
        if _match_word(parser, "prompt"):
            _ensure_unique("prompt", prompt if prompt_expr is None else object(), tok)
            parser._expect("IS", "Expected 'is' after prompt")
            prompt_value = parser._parse_expression()
            if isinstance(prompt_value, ast.Literal) and isinstance(prompt_value.value, str):
                prompt = prompt_value.value
                prompt_expr = None
            else:
                prompt = None
                prompt_expr = prompt_value
            parser._match("NEWLINE")
            continue
        if _match_word(parser, "dataset"):
            _ensure_unique("dataset", dataset, tok)
            parser._expect("IS", "Expected 'is' after dataset")
            value_tok = parser._expect("STRING", "Expected dataset string")
            dataset = value_tok.value
            parser._match("NEWLINE")
            continue
        if _match_word(parser, "source_language"):
            _ensure_unique("source_language", source_language, tok)
            parser._expect("IS", "Expected 'is' after source_language")
            value_tok = parser._expect("STRING", "Expected source language code")
            source_language = value_tok.value
            parser._match("NEWLINE")
            continue
        if _match_word(parser, "target_language"):
            _ensure_unique("target_language", target_language, tok)
            parser._expect("IS", "Expected 'is' after target_language")
            value_tok = parser._expect("STRING", "Expected target language code")
            target_language = value_tok.value
            parser._match("NEWLINE")
            continue
        if _match_word(parser, "output"):
            if parser._match("IS"):
                _ensure_unique("output", output_type, tok)
                if output_fields is not None:
                    raise Namel3ssError(
                        "AI flow cannot declare both `output is` and an `output:` block",
                        line=tok.line,
                        column=tok.column,
                    )
                output_type, _, _, _, _ = parse_type_reference(parser)
                parser._match("NEWLINE")
                continue
            if parser._match("COLON"):
                _ensure_unique("output", output_fields, tok)
                if output_type is not None:
                    raise Namel3ssError(
                        "AI flow cannot declare both `output is` and an `output:` block",
                        line=tok.line,
                        column=tok.column,
                    )
                output_fields = _parse_output_fields_block(parser, header_tok=tok)
                continue
            raise Namel3ssError("Expected `is` or `:` after output", line=tok.line, column=tok.column)
        if kind == "rag" and _match_word(parser, "sources"):
            _ensure_unique("sources", sources, tok)
            sources = _parse_value_block(parser, label="sources", allow_strings=False)
            continue
        if kind == "classification" and _match_word(parser, "labels"):
            _ensure_unique("labels", labels, tok)
            labels = _parse_value_block(parser, label="labels", allow_strings=True)
            continue
        if kind == "chain" and _match_word(parser, "steps"):
            _ensure_unique("steps", chain_steps, tok)
            chain_steps = _parse_chain_steps_block(parser, header_tok=tok)
            continue
        if _match_word(parser, "tests"):
            _ensure_unique("tests", tests, tok)
            tests = _parse_tests_block(parser, header_tok=tok)
            continue
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unknown {kind} field '{tok.value}'.",
                why="This AI flow field is not supported for the current pattern.",
                fix="Remove the line or use a supported field.",
                example=(
                    f'{raw_kind} "example":\n'
                    '  model is "gpt-4"\n'
                    '  prompt is "Qn: hello"\n'
                    "  output is text"
                ),
            ),
            line=tok.line,
            column=tok.column,
        )
    parser._expect("DEDENT", "Expected end of AI flow block")
    while parser._match("NEWLINE"):
        pass
    _validate_required_fields(
        kind=kind,
        model=model,
        prompt=prompt,
        prompt_expr=prompt_expr,
        source_language=source_language,
        target_language=target_language,
        labels=labels,
        sources=sources,
        output_fields=output_fields,
        chain_steps=chain_steps,
        line=kind_tok.line,
        column=kind_tok.column,
    )
    if output_type is None and output_fields is None and kind != "chain":
        output_type = "text"
    return ast.AIFlowDefinition(
        name=name_tok.value,
        kind=kind,
        model=model,
        prompt=prompt,
        prompt_expr=prompt_expr,
        dataset=dataset,
        output_type=output_type,
        source_language=source_language,
        target_language=target_language,
        output_fields=output_fields,
        labels=labels,
        sources=sources,
        chain_steps=chain_steps,
        tests=tests,
        return_expr=return_expr,
        line=kind_tok.line,
        column=kind_tok.column,
    )
def _parse_output_fields_block(parser, *, header_tok) -> list[ast.AIOutputField]:
    parser._expect("NEWLINE", "Expected newline after output")
    parser._expect("INDENT", "Expected indented output block")
    fields: list[ast.AIOutputField] = []
    seen: set[str] = set()
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        name_tok = parser._expect("IDENT", "Expected output field name")
        parser._expect("IS", "Expected 'is' after output field name")
        type_name, _, _, _, _ = parse_type_reference(parser)
        if name_tok.value in seen:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Output field '{name_tok.value}' is duplicated.",
                    why="Output field names must be unique.",
                    fix="Rename or remove the duplicate field.",
                    example="output:\n  ans is text",
                ),
                line=name_tok.line,
                column=name_tok.column,
            )
        seen.add(name_tok.value)
        fields.append(
            ast.AIOutputField(
                name=name_tok.value,
                type_name=type_name,
                line=name_tok.line,
                column=name_tok.column,
            )
        )
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of output block")
    while parser._match("NEWLINE"):
        pass
    if not fields:
        raise Namel3ssError(
            build_guidance_message(
                what="Output block has no fields.",
                why="Output blocks require one or more fields.",
                fix="Add one or more `name is type` lines.",
                example="output:\n  ans is text",
            ),
            line=header_tok.line,
            column=header_tok.column,
        )
    return fields
def _parse_chain_steps_block(parser, *, header_tok) -> list[ast.ChainStep]:
    parser._expect("COLON", "Expected ':' after steps")
    parser._expect("NEWLINE", "Expected newline after steps")
    parser._expect("INDENT", "Expected indented steps block")
    steps: list[ast.ChainStep] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        step_tok = parser._expect("MINUS", "Expected '-' to start a chain step")
        if not _match_word(parser, "call"):
            raise Namel3ssError("Chain step must start with call", line=step_tok.line, column=step_tok.column)
        flow_kind = None
        if parser._current().type != "STRING":
            token = parser._current()
            if not isinstance(token.value, str) or not token.value:
                raise Namel3ssError("Expected flow type before flow name", line=token.line, column=token.column)
            parser._advance()
            flow_kind = _normalize_kind(token.value)
        name_tok = parser._expect("STRING", "Expected called flow name string")
        if not _match_word(parser, "with"):
            raise Namel3ssError(
                "Chain step must include `with` before input expression",
                line=name_tok.line,
                column=name_tok.column,
            )
        input_expr = parser._parse_expression()
        parser._match("NEWLINE")
        steps.append(
            ast.ChainStep(
                flow_kind=flow_kind,
                flow_name=name_tok.value,
                input_expr=input_expr,
                line=step_tok.line,
                column=step_tok.column,
            )
        )
    parser._expect("DEDENT", "Expected end of steps block")
    while parser._match("NEWLINE"):
        pass
    if not steps:
        raise Namel3ssError(
            build_guidance_message(
                what="Steps block has no entries.",
                why="Chain flows require at least one step.",
                fix="Add one or more call steps.",
                example='steps:\n  - call summarise "summarise_doc" with input.document',
            ),
            line=header_tok.line,
            column=header_tok.column,
        )
    return steps
def _parse_tests_block(parser, *, header_tok) -> ast.AIFlowTestConfig:
    parser._expect("COLON", "Expected ':' after tests")
    parser._expect("NEWLINE", "Expected newline after tests")
    parser._expect("INDENT", "Expected indented tests block")
    dataset = None
    metrics: list[str] | None = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if _match_word(parser, "dataset"):
            if dataset is not None:
                raise Namel3ssError("tests dataset is declared more than once", line=tok.line, column=tok.column)
            parser._expect("IS", "Expected 'is' after dataset")
            dataset_tok = parser._expect("STRING", "Expected dataset string")
            dataset = dataset_tok.value
            parser._match("NEWLINE")
            continue
        if _match_word(parser, "metrics"):
            if metrics is not None:
                raise Namel3ssError("tests metrics are declared more than once", line=tok.line, column=tok.column)
            metrics = _parse_metric_list_block(parser, header_tok=tok)
            continue
        raise Namel3ssError("Unknown tests field", line=tok.line, column=tok.column)
    parser._expect("DEDENT", "Expected end of tests block")
    while parser._match("NEWLINE"):
        pass
    if dataset is None:
        raise Namel3ssError("tests block is missing dataset", line=header_tok.line, column=header_tok.column)
    if not metrics:
        raise Namel3ssError("tests block is missing metrics", line=header_tok.line, column=header_tok.column)
    return ast.AIFlowTestConfig(dataset=dataset, metrics=metrics, line=header_tok.line, column=header_tok.column)
def _parse_metric_list_block(parser, *, header_tok) -> list[str]:
    parser._expect("COLON", "Expected ':' after metrics")
    parser._expect("NEWLINE", "Expected newline after metrics")
    parser._expect("INDENT", "Expected indented metrics block")
    values: list[str] = []
    seen: set[str] = set()
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        item_tok = parser._expect("MINUS", "Expected '-' for metrics entry")
        value_tok = parser._current()
        if value_tok.type not in {"IDENT", "STRING"}:
            raise Namel3ssError("Metric name must be text", line=value_tok.line, column=value_tok.column)
        parser._advance()
        value = str(value_tok.value).strip()
        if not value:
            raise Namel3ssError("Metric name cannot be empty", line=value_tok.line, column=value_tok.column)
        if value in seen:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Metric '{value}' is duplicated.",
                    why="Each metric can appear only once.",
                    fix="Remove the duplicate metric.",
                    example="metrics:\n  - accuracy",
                ),
                line=item_tok.line,
                column=item_tok.column,
            )
        seen.add(value)
        values.append(value)
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of metrics block")
    while parser._match("NEWLINE"):
        pass
    return values
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
def _validate_required_fields(
    *,
    kind: str,
    model: str | None,
    prompt: str | None,
    prompt_expr,
    source_language: str | None,
    target_language: str | None,
    labels: list[str] | None,
    sources: list[str] | None,
    output_fields: list[ast.AIOutputField] | None,
    chain_steps: list[ast.ChainStep] | None,
    line: int | None,
    column: int | None,
) -> None:
    if kind != "chain":
        if model is None:
            raise Namel3ssError("AI flow is missing a model", line=line, column=column)
        if prompt is None and prompt_expr is None:
            raise Namel3ssError("AI flow is missing a prompt", line=line, column=column)
    if kind == "translate":
        if source_language is None:
            raise Namel3ssError("Translate flow is missing source_language", line=line, column=column)
        if target_language is None:
            raise Namel3ssError("Translate flow is missing target_language", line=line, column=column)
    if kind == "rag" and not sources:
        raise Namel3ssError("RAG flow is missing sources", line=line, column=column)
    if kind == "classification" and not labels:
        raise Namel3ssError("Classification flow is missing labels", line=line, column=column)
    if kind == "qa":
        names = {field.name for field in output_fields or []}
        if "ans" not in names:
            raise Namel3ssError("QA flow output block must include ans", line=line, column=column)
    if kind == "cot":
        names = {field.name for field in output_fields or []}
        missing = [name for name in ("reasoning", "ans") if name not in names]
        if missing:
            joined = ", ".join(missing)
            raise Namel3ssError(f"COT flow output is missing {joined}", line=line, column=column)
    if kind == "chain":
        if not chain_steps:
            raise Namel3ssError("Chain flow is missing steps", line=line, column=column)
        if not output_fields:
            raise Namel3ssError("Chain flow is missing output block", line=line, column=column)
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
def _match_word(parser, value: str) -> bool:
    tok = parser._current()
    if tok.value == value:
        parser._advance()
        return True
    return False
def _normalize_kind(value: str) -> str:
    lowered = str(value or "").strip().lower()
    return _KIND_ALIASES.get(lowered, lowered)
