from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


_MODULE_CATEGORIES = ("functions", "records", "tools", "pages")


def parse_use_decl(parser) -> ast.UseDecl:
    use_tok = parser._advance()
    module_keyword = False
    module_tok = parser._current()
    if module_tok.type == "IDENT" and module_tok.value == "module":
        module_keyword = True
        parser._advance()
        module_tok = parser._current()
    if module_tok.type != "STRING":
        if module_keyword:
            raise Namel3ssError(
                build_guidance_message(
                    what="Use module is missing a path.",
                    why="Modules are referenced by path strings from the project root.",
                    fix='Use module "modules/common.ai" as common.',
                    example='use module "modules/common.ai" as common',
                ),
                line=module_tok.line,
                column=module_tok.column,
            )
        raise Namel3ssError(
            build_guidance_message(
                what="Use statement is missing a module name.",
                why="Modules are referenced by name strings under the modules folder.",
                fix='Use "use \"inventory\" as inv" with a module name string.',
                example='use "inventory" as inv',
            ),
            line=module_tok.line,
            column=module_tok.column,
        )
    parser._advance()
    if not parser._match("AS"):
        tok = parser._current()
        raise Namel3ssError(
            build_guidance_message(
                what="Use statement is missing `as`.",
                why="`as` introduces the required namespace alias.",
                fix='Use `use "<module>" as <alias>`.',
                example='use "inventory" as inv',
            ),
            line=tok.line,
            column=tok.column,
        )
    alias_tok = parser._current()
    if alias_tok.type != "IDENT":
        raise Namel3ssError(
            build_guidance_message(
                what="Use statement is missing an alias.",
                why="Aliases keep cross-module references explicit and deterministic.",
                fix="Provide a short alias after `as`.",
                example='use "inventory" as inv',
            ),
            line=alias_tok.line,
            column=alias_tok.column,
        )
    parser._advance()
    only: list[str] = []
    allow_override: list[str] = []
    if module_keyword:
        only, allow_override = _parse_use_trailers(parser, module_tok)
    return ast.UseDecl(
        module=module_tok.value,
        alias=alias_tok.value,
        module_path=module_tok.value if module_keyword else None,
        only=only,
        allow_override=allow_override,
        line=use_tok.line,
        column=use_tok.column,
    )


def _parse_use_trailers(parser, module_tok) -> tuple[list[str], list[str]]:
    only: list[str] = []
    allow_override: list[str] = []
    seen_only = False
    seen_allow = False
    while True:
        while parser._match("NEWLINE"):
            pass
        tok = parser._current()
        if tok.type == "IDENT" and tok.value == "only":
            if seen_only:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Use module has more than one only block.",
                        why="Each use module statement can declare only once.",
                        fix="Keep a single only block after the use statement.",
                        example='use module "modules/common.ai" as common\nonly:\n  functions',
                    ),
                    line=tok.line,
                    column=tok.column,
                )
            seen_only = True
            only = _parse_use_block(parser, label="only")
            continue
        if tok.type == "IDENT" and tok.value == "allow":
            if seen_allow:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Use module has more than one allow override block.",
                        why="Each use module statement can declare allow override once.",
                        fix="Keep a single allow override block after the use statement.",
                        example='use module "modules/common.ai" as common\nallow override:\n  tools',
                    ),
                    line=tok.line,
                    column=tok.column,
                )
            seen_allow = True
            allow_override = _parse_allow_override_block(parser)
            continue
        break
    _validate_use_categories(only, module_tok, label="only")
    _validate_use_categories(allow_override, module_tok, label="allow override")
    return only, allow_override


def _parse_allow_override_block(parser) -> list[str]:
    allow_tok = parser._advance()
    override_tok = parser._current()
    if override_tok.type != "IDENT" or override_tok.value != "override":
        raise Namel3ssError(
            build_guidance_message(
                what="Allow override block is missing override.",
                why="Use allow override as a two word header.",
                fix="Use allow override followed by a colon.",
                example='allow override:\n  functions',
            ),
            line=override_tok.line,
            column=override_tok.column,
        )
    parser._advance()
    return _parse_use_block(parser, label="allow override", header_tok=allow_tok)


def _parse_use_block(parser, *, label: str, header_tok=None) -> list[str]:
    header_tok = header_tok or parser._advance()
    parser._expect("COLON", f"Expected ':' after {label}")
    parser._expect("NEWLINE", f"Expected newline after {label}")
    parser._expect("INDENT", f"Expected indented {label} block")
    categories: list[str] = []
    seen = set()
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        cat_tok = parser._current()
        cat = _parse_use_category(parser)
        if cat in seen:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Duplicate category in {label}.",
                    why="Each category can appear once.",
                    fix="Keep each category on a single line.",
                    example=f"{label}:\n  {cat}",
                ),
                line=cat_tok.line,
                column=cat_tok.column,
            )
        seen.add(cat)
        categories.append(cat)
        parser._match("NEWLINE")
    parser._expect("DEDENT", f"Expected end of {label} block")
    while parser._match("NEWLINE"):
        pass
    if not categories:
        raise Namel3ssError(
            build_guidance_message(
                what=f"{label} block is empty.",
                why="Each block must list at least one category.",
                fix="Add one or more categories.",
                example=f"{label}:\n  functions",
            ),
            line=header_tok.line if header_tok else None,
            column=header_tok.column if header_tok else None,
        )
    return categories


def _parse_use_category(parser) -> str:
    tok = parser._current()
    if tok.type == "TOOLS":
        parser._advance()
        return "tools"
    if tok.type == "TOOL":
        parser._advance()
        return "tools"
    if tok.type == "RECORD":
        parser._advance()
        return "records"
    if tok.type == "PAGE":
        parser._advance()
        return "pages"
    if tok.type == "IDENT":
        value = tok.value
        if value in {"function", "functions"}:
            parser._advance()
            return "functions"
        if value in {"record", "records"}:
            parser._advance()
            return "records"
        if value in {"page", "pages"}:
            parser._advance()
            return "pages"
        if value in {"tool", "tools"}:
            parser._advance()
            return "tools"
    raise Namel3ssError(
        build_guidance_message(
            what="Use module block has an unknown category.",
            why="Only functions, records, tools, and pages are supported.",
            fix="Use one of the supported categories.",
            example="only:\n  functions\n  records",
        ),
        line=tok.line,
        column=tok.column,
    )


def _validate_use_categories(categories: list[str], module_tok, *, label: str) -> None:
    for item in categories:
        if item not in _MODULE_CATEGORIES:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"{label} has an unknown category.",
                    why="Only functions, records, tools, and pages are supported.",
                    fix="Use a supported category name.",
                    example="only:\n  functions\n  records",
                ),
                line=module_tok.line,
                column=module_tok.column,
            )


__all__ = ["parse_use_decl"]
