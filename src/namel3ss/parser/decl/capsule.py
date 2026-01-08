from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


ALLOWED_EXPORT_KINDS = {
    "RECORD": "record",
    "FLOW": "flow",
    "PAGE": "page",
    "AI": "ai",
    "AGENT": "agent",
    "TOOL": "tool",
}


def parse_capsule_decl(parser) -> ast.CapsuleDecl:
    capsule_tok = parser._advance()
    name_tok = parser._current()
    if name_tok.type != "STRING":
        raise Namel3ssError(
            build_guidance_message(
                what="Capsule declaration is missing a name.",
                why="Capsule names must match the module folder name.",
                fix='Use `capsule "<name>":` at the top of capsule.ai.',
                example='capsule "inventory":',
            ),
            line=name_tok.line,
            column=name_tok.column,
        )
    capsule_name = name_tok.value
    parser._advance()
    parser._expect("COLON", "Expected ':' after capsule name")
    parser._expect("NEWLINE", "Expected newline after capsule header")
    parser._expect("INDENT", "Expected indented capsule body")
    exports: list[ast.CapsuleExport] = []
    saw_exports = False
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        key_tok = parser._current()
        if key_tok.type == "IDENT" and key_tok.value == "exports":
            if saw_exports:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Capsule exports block is duplicated.",
                        why="Each capsule.ai may only declare one exports block.",
                        fix="Keep a single `exports:` section.",
                        example='exports:\n  flow "calc_total"',
                    ),
                    line=key_tok.line,
                    column=key_tok.column,
                )
            saw_exports = True
            parser._advance()
            parser._expect("COLON", "Expected ':' after exports")
            parser._expect("NEWLINE", "Expected newline after exports")
            parser._expect("INDENT", "Expected indented exports block")
            while parser._current().type != "DEDENT":
                if parser._match("NEWLINE"):
                    continue
                export_tok = parser._current()
                export_kind = None
                if export_tok.type in ALLOWED_EXPORT_KINDS:
                    export_kind = ALLOWED_EXPORT_KINDS[export_tok.type]
                elif export_tok.type == "IDENT" and export_tok.value == "function":
                    export_kind = "function"
                elif export_tok.type == "IDENT" and export_tok.value == "ui_pack":
                    export_kind = "ui_pack"
                if export_kind is None:
                    raise Namel3ssError(
                        build_guidance_message(
                            what="Unsupported export entry in capsule.",
                            why="Exports must be record, flow, page, ai, agent, tool, function, or ui_pack names.",
                            fix="List exported symbols with their type.",
                            example='exports:\n  record "Product"\n  flow "calc_total"',
                        ),
                        line=export_tok.line,
                        column=export_tok.column,
                    )
                parser._advance()
                name_tok = parser._current()
                if name_tok.type != "STRING":
                    raise Namel3ssError(
                        build_guidance_message(
                            what="Export entry is missing a name.",
                            why="Exports must name the symbol being exposed.",
                            fix="Provide a quoted name after the export type.",
                            example='flow "calc_total"',
                        ),
                        line=name_tok.line,
                        column=name_tok.column,
                    )
                parser._advance()
                exports.append(
                    ast.CapsuleExport(
                        kind=export_kind,
                        name=name_tok.value,
                        line=export_tok.line,
                        column=export_tok.column,
                    )
                )
                parser._match("NEWLINE")
            parser._expect("DEDENT", "Expected end of exports block")
            continue
        raise Namel3ssError(
            build_guidance_message(
                what="Unexpected entry in capsule file.",
                why="Capsule files only declare exported symbols.",
                fix="Define exports inside the `exports:` block.",
                example='capsule "inventory":\n  exports:\n    record "Product"',
            ),
            line=key_tok.line,
            column=key_tok.column,
        )
    parser._expect("DEDENT", "Expected end of capsule body")
    if not saw_exports:
        raise Namel3ssError(
            build_guidance_message(
                what="Capsule is missing an exports block.",
                why="Exports define the public API for the module.",
                fix="Add an exports section listing records/flows/pages/etc.",
                example='capsule "inventory":\n  exports:\n    record "Product"',
            ),
            line=capsule_tok.line,
            column=capsule_tok.column,
        )
    return ast.CapsuleDecl(name=capsule_name, exports=exports, line=capsule_tok.line, column=capsule_tok.column)


__all__ = ["parse_capsule_decl", "ALLOWED_EXPORT_KINDS"]
