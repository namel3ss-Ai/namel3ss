from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.parser.decl.type_reference import parse_type_reference


_ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


def parse_route_decl(parser) -> ast.RouteDefinition:
    route_tok = parser._advance()
    name_tok = parser._expect("STRING", "Expected route name string")
    parser._expect("COLON", "Expected ':' after route name")
    parser._expect("NEWLINE", "Expected newline after route header")
    parser._expect("INDENT", "Expected indented route block")

    path = None
    method = None
    parameters = None
    request = None
    response = None
    flow_name = None
    upload = None
    seen_upload = False

    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if seen_upload:
            raise Namel3ssError(
                build_guidance_message(
                    what="Upload must appear after other route fields.",
                    why="The upload flag is always the final line in a route block.",
                    fix="Move upload to the bottom of the route block.",
                    example=(
                        'route "upload":\n'
                        '  path is "/api/upload"\n'
                        '  method is "POST"\n'
                        '  response:\n'
                        '    ok is boolean\n'
                        '  flow is "upload_file"\n'
                        '  upload is true'
                    ),
                ),
                line=tok.line,
                column=tok.column,
            )
        if _match_ident(parser, "path"):
            _ensure_unique("path", path, tok)
            parser._expect("IS", "Expected 'is' after path")
            value_tok = parser._expect("STRING", "Expected path string")
            path = value_tok.value
            parser._match("NEWLINE")
            continue
        if _match_ident(parser, "method"):
            _ensure_unique("method", method, tok)
            parser._expect("IS", "Expected 'is' after method")
            value_tok = parser._expect("STRING", "Expected method string")
            method = value_tok.value
            parser._match("NEWLINE")
            continue
        if _match_ident(parser, "parameters"):
            _ensure_unique("parameters", parameters, tok)
            parameters = _parse_field_block(parser, section="parameters")
            continue
        if _match_ident(parser, "request"):
            _ensure_unique("request", request, tok)
            request = _parse_field_block(parser, section="request")
            continue
        if _match_ident(parser, "response"):
            _ensure_unique("response", response, tok)
            response = _parse_field_block(parser, section="response")
            continue
        if tok.type == "FLOW":
            parser._advance()
            _ensure_unique("flow", flow_name, tok)
            parser._expect("IS", "Expected 'is' after flow")
            value_tok = parser._expect("STRING", "Expected flow name string")
            flow_name = value_tok.value
            parser._match("NEWLINE")
            continue
        if _match_ident(parser, "upload"):
            _ensure_unique("upload", upload, tok)
            parser._expect("IS", "Expected 'is' after upload")
            value_tok = parser._expect("BOOLEAN", "Expected true after upload")
            if value_tok.value is not True:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Upload flag must be true.",
                        why="Routes either declare upload support or omit the flag.",
                        fix="Use upload is true or remove the line.",
                        example='upload is true',
                    ),
                    line=value_tok.line,
                    column=value_tok.column,
                )
            upload = True
            seen_upload = True
            parser._match("NEWLINE")
            continue
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unknown route field '{tok.value}'.",
                why="Route blocks only allow path, method, parameters, request, response, flow, and upload.",
                fix="Remove the line or use a supported field.",
                example=(
                    'route "list_users":\n'
                    '  path is "/api/users"\n'
                    '  method is "GET"\n'
                    '  response:\n'
                    '    users is list<User>\n'
                    '  flow is "get_users"'
                ),
            ),
            line=tok.line,
            column=tok.column,
        )

    parser._expect("DEDENT", "Expected end of route block")
    while parser._match("NEWLINE"):
        pass

    if path is None:
        raise Namel3ssError("Route is missing a path", line=route_tok.line, column=route_tok.column)
    if method is None:
        raise Namel3ssError("Route is missing a method", line=route_tok.line, column=route_tok.column)
    method_value = str(method).upper()
    if method_value not in _ALLOWED_METHODS:
        raise Namel3ssError(
            f"Unsupported HTTP method '{method}'.",
            line=route_tok.line,
            column=route_tok.column,
        )
    if response is None:
        raise Namel3ssError("Route is missing a response block", line=route_tok.line, column=route_tok.column)
    if flow_name is None:
        raise Namel3ssError("Route is missing a flow", line=route_tok.line, column=route_tok.column)

    return ast.RouteDefinition(
        name=name_tok.value,
        path=path,
        method=method_value,
        parameters=parameters or {},
        request=request,
        response=response,
        flow_name=flow_name,
        upload=upload,
        line=route_tok.line,
        column=route_tok.column,
    )


def _parse_field_block(parser, *, section: str) -> dict[str, ast.RouteField]:
    parser._expect("COLON", f"Expected ':' after {section}")
    parser._expect("NEWLINE", f"Expected newline after {section}")
    if not parser._match("INDENT"):
        raise Namel3ssError(
            build_guidance_message(
                what=f"{section.title()} block has no fields.",
                why=f"{section.title()} blocks require at least one field declaration.",
                fix=f"Add one or more fields under {section}.",
                example=f"{section}:\n  name is text",
            ),
            line=parser._current().line,
            column=parser._current().column,
        )
    fields: dict[str, ast.RouteField] = {}
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        name_tok = parser._expect("IDENT", f"Expected {section} field name")
        parser._expect("IS", "Expected 'is' after field name")
        type_name, type_was_alias, raw_type_name, type_line, type_column = parse_type_reference(parser)
        if name_tok.value in fields:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"{section.title()} field '{name_tok.value}' is duplicated.",
                    why="Each field may only be declared once.",
                    fix="Remove the duplicate or rename it.",
                    example=f'{name_tok.value} is {type_name}',
                ),
                line=name_tok.line,
                column=name_tok.column,
            )
        fields[name_tok.value] = ast.RouteField(
            name=name_tok.value,
            type_name=type_name,
            type_was_alias=type_was_alias,
            raw_type_name=raw_type_name,
            type_line=type_line,
            type_column=type_column,
            line=name_tok.line,
            column=name_tok.column,
        )
        parser._match("NEWLINE")
    parser._expect("DEDENT", f"Expected end of {section} block")
    while parser._match("NEWLINE"):
        pass
    if not fields:
        raise Namel3ssError(
            build_guidance_message(
                what=f"{section.title()} block has no fields.",
                why=f"{section.title()} blocks require at least one field declaration.",
                fix=f"Add one or more fields under {section}.",
                example=f"{section}:\n  name is text",
            ),
            line=parser._current().line,
            column=parser._current().column,
        )
    return fields


def _ensure_unique(field: str, current: object | None, tok) -> None:
    if current is None:
        return
    raise Namel3ssError(
        build_guidance_message(
            what=f"Route declares {field} more than once.",
            why="Each route field may only be declared once.",
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


__all__ = ["parse_route_decl"]
