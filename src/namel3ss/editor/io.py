from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from namel3ss.ast import nodes as ast
from namel3ss.lexer.lexer import Lexer
from namel3ss.lexer.tokens import Token
from namel3ss.module_loader.types import ModuleExports


TRIVIA_TOKENS = {"NEWLINE", "INDENT", "DEDENT", "EOF"}


@dataclass(frozen=True)
class TextSpan:
    line: int
    column: int
    end_line: int
    end_column: int

    def contains(self, line: int, column: int) -> bool:
        if line != self.line or line != self.end_line:
            return False
        return self.column <= column < self.end_column


@dataclass(frozen=True)
class TokenSpan:
    type: str
    value: object | None
    line: int
    column: int
    end_column: int


@dataclass(frozen=True)
class SymbolDefinition:
    kind: str
    name: str
    module: str | None
    file: Path
    span: TextSpan
    origin: str
    exported: bool


@dataclass(frozen=True)
class SymbolReference:
    kind: str
    raw_name: str
    file: Path
    span: TextSpan
    replace_span: TextSpan
    is_string: bool


@dataclass(frozen=True)
class FileIndex:
    path: Path
    module: str | None
    origin: str
    uses: Dict[str, str]
    definitions: List[SymbolDefinition]
    references: List[SymbolReference]


@dataclass(frozen=True)
class ProjectIndex:
    root: Path
    files: Dict[Path, FileIndex]
    definitions: Dict[Tuple[str | None, str, str], SymbolDefinition]
    nodes: Dict[Tuple[str | None, str, str], ast.Node]
    exports: Dict[str, ModuleExports]


def _module_context(path: Path, root: Path) -> tuple[str | None, str]:
    try:
        rel = path.resolve().relative_to(root.resolve())
    except ValueError:
        return None, "external"
    if not rel.parts:
        return None, "app"
    if rel.parts[0] == "modules" and len(rel.parts) > 1:
        return rel.parts[1], "module"
    if rel.parts[0] == "packages" and len(rel.parts) > 1:
        return rel.parts[1], "package"
    return None, "app"


def _scan_file(
    *,
    path: Path,
    source: str,
    module_name: str | None,
    origin: str,
    exports: Dict[str, ModuleExports],
) -> FileIndex:
    tokens = _tokenize(source)
    definitions: List[SymbolDefinition] = []
    references: List[SymbolReference] = []
    uses: Dict[str, str] = {}

    i = 0
    while i < len(tokens):
        tok = tokens[i]
        next_tok = _peek(tokens, i + 1)

        if tok.type == "IDENT" and tok.value == "use":
            module_tok = _peek(tokens, i + 1)
            as_tok = _peek(tokens, i + 2)
            alias_tok = _peek(tokens, i + 3)
            if module_tok and module_tok.type == "STRING" and as_tok and as_tok.type == "AS" and alias_tok and alias_tok.type == "IDENT":
                uses[str(alias_tok.value)] = str(module_tok.value)
                span = TextSpan(module_tok.line, module_tok.column, module_tok.line, module_tok.end_column)
                references.append(
                    SymbolReference(
                        kind="capsule",
                        raw_name=str(module_tok.value),
                        file=path,
                        span=span,
                        replace_span=span,
                        is_string=True,
                    )
                )
                i += 4
                continue

        if _is_definition(tokens, i, "RECORD"):
            name_tok = tokens[i + 1]
            definitions.append(_make_definition("record", name_tok, module_name, path, origin, exports))
            i += 2
            continue
        if _is_definition(tokens, i, "FLOW"):
            name_tok = tokens[i + 1]
            definitions.append(_make_definition("flow", name_tok, module_name, path, origin, exports))
            i += 2
            continue
        if _is_definition(tokens, i, "JOB"):
            name_tok = tokens[i + 1]
            definitions.append(_make_definition("job", name_tok, module_name, path, origin, exports))
            i += 2
            continue
        if _is_definition(tokens, i, "PAGE"):
            name_tok = tokens[i + 1]
            definitions.append(_make_definition("page", name_tok, module_name, path, origin, exports))
            i += 2
            continue
        if _is_definition(tokens, i, "AI"):
            name_tok = tokens[i + 1]
            definitions.append(_make_definition("ai", name_tok, module_name, path, origin, exports))
            i += 2
            continue
        if _is_definition(tokens, i, "TOOL"):
            name_tok = tokens[i + 1]
            definitions.append(_make_definition("tool", name_tok, module_name, path, origin, exports))
            i += 2
            continue
        if _is_definition(tokens, i, "AGENT"):
            name_tok = tokens[i + 1]
            definitions.append(_make_definition("agent", name_tok, module_name, path, origin, exports))
            i += 2
            continue
        if _is_ident_definition(tokens, i, "identity"):
            name_tok = tokens[i + 1]
            definitions.append(_make_definition("identity", name_tok, None, path, origin, exports))
            i += 2
            continue
        if _is_ident_definition(tokens, i, "capsule"):
            name_tok = tokens[i + 1]
            definitions.append(_make_definition("capsule", name_tok, None, path, origin, exports))
            i += 2
            continue

        if tok.type == "CALLS" and next_tok and next_tok.type == "FLOW":
            ref, consumed = _parse_reference(tokens, i + 2)
            if ref:
                references.append(_make_reference("flow", ref, path))
                i += consumed + 2
                continue
        if tok.type == "ENQUEUE" and next_tok and next_tok.type == "JOB":
            ref, consumed = _parse_reference(tokens, i + 2)
            if ref:
                references.append(_make_reference("job", ref, path))
                i += consumed + 2
                continue
        if tok.type == "FORM" and next_tok and next_tok.type == "IS":
            ref, consumed = _parse_reference(tokens, i + 2)
            if ref:
                references.append(_make_reference("record", ref, path))
                i += consumed + 2
                continue
        if tok.type == "TABLE" and next_tok and next_tok.type == "IS":
            ref, consumed = _parse_reference(tokens, i + 2)
            if ref:
                references.append(_make_reference("record", ref, path))
                i += consumed + 2
                continue
        if tok.type == "SAVE":
            ref, consumed = _parse_reference(tokens, i + 1)
            if ref:
                references.append(_make_reference("record", ref, path))
                i += consumed + 1
                continue
        if tok.type == "CREATE":
            ref, consumed = _parse_reference(tokens, i + 1)
            if ref:
                references.append(_make_reference("record", ref, path))
                i += consumed + 1
                continue
        if tok.type == "FIND":
            ref, consumed = _parse_reference(tokens, i + 1)
            if ref:
                references.append(_make_reference("record", ref, path))
                i += consumed + 1
                continue
        if tok.type == "ASK" and next_tok and next_tok.type == "AI":
            ref, consumed = _parse_reference(tokens, i + 2)
            if ref:
                references.append(_make_reference("ai", ref, path))
                i += consumed + 2
                continue
        if tok.type == "RUN" and next_tok and next_tok.type == "AGENT":
            ref, consumed = _parse_reference(tokens, i + 2)
            if ref:
                references.append(_make_reference("agent", ref, path))
                i += consumed + 2
                continue
        if tok.type == "AGENT":
            ref, consumed = _parse_reference(tokens, i + 1)
            if ref:
                after_ref = _peek(tokens, i + 1 + consumed)
                if after_ref and after_ref.type == "WITH":
                    references.append(_make_reference("agent", ref, path))
                    i += consumed + 1
                    continue
        if tok.type == "AI" and next_tok and next_tok.type == "IS":
            ref, consumed = _parse_reference(tokens, i + 2)
            if ref:
                references.append(_make_reference("ai", ref, path))
                i += consumed + 2
                continue
        if tok.type == "EXPOSE":
            ref, consumed = _parse_reference(tokens, i + 1)
            if ref:
                references.append(_make_reference("tool", ref, path))
                i += consumed + 1
                continue

        if path.name == "capsule.ai" and tok.type in {"RECORD", "FLOW", "JOB", "PAGE", "AI", "AGENT", "TOOL"}:
            ref, consumed = _parse_reference(tokens, i + 1)
            if ref:
                kind = tok.type.lower()
                references.append(_make_reference(kind, ref, path))
                i += consumed + 1
                continue

        i += 1

    return FileIndex(
        path=path,
        module=module_name,
        origin=origin,
        uses=uses,
        definitions=definitions,
        references=references,
    )


def _tokenize(source: str) -> List[TokenSpan]:
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    spans: List[TokenSpan] = []
    for tok in tokens:
        if tok.type in TRIVIA_TOKENS:
            continue
        length = _token_length(tok)
        spans.append(TokenSpan(tok.type, tok.value, tok.line, tok.column, tok.column + length))
    return spans


def _token_length(tok: Token) -> int:
    if tok.type in {"INDENT", "DEDENT", "NEWLINE", "EOF"}:
        return 0
    if tok.type == "STRING":
        return len(str(tok.value)) + 2
    if tok.type == "NUMBER":
        return len(str(tok.value))
    if tok.type == "BOOLEAN":
        return 4 if tok.value else 5
    if tok.value is None:
        return 1
    return len(str(tok.value))


def _peek(tokens: List[TokenSpan], index: int) -> Optional[TokenSpan]:
    if 0 <= index < len(tokens):
        return tokens[index]
    return None


def _is_definition(tokens: List[TokenSpan], index: int, token_type: str) -> bool:
    if index < 0 or index >= len(tokens):
        return False
    tok = tokens[index]
    if tok.type != token_type:
        return False
    name_tok = _peek(tokens, index + 1)
    after_name = _peek(tokens, index + 2)
    if not name_tok or name_tok.type != "STRING":
        return False
    return bool(after_name and after_name.type == "COLON")


def _is_ident_definition(tokens: List[TokenSpan], index: int, ident: str) -> bool:
    tok = _peek(tokens, index)
    name_tok = _peek(tokens, index + 1)
    after = _peek(tokens, index + 2)
    if not tok or tok.type != "IDENT" or tok.value != ident:
        return False
    if not name_tok or name_tok.type != "STRING":
        return False
    return bool(after and after.type == "COLON")


def _parse_reference(tokens: List[TokenSpan], index: int) -> tuple[SymbolReference | None, int]:
    tok = _peek(tokens, index)
    if not tok:
        return None, 0
    if tok.type == "STRING":
        span = TextSpan(tok.line, tok.column, tok.line, tok.end_column)
        ref = SymbolReference(
            kind="",
            raw_name=str(tok.value),
            file=Path(),
            span=span,
            replace_span=span,
            is_string=True,
        )
        return ref, 1
    if tok.type != "IDENT":
        return None, 0
    parts = [str(tok.value)]
    end_tok = tok
    consumed = 1
    j = index + 1
    while True:
        dot = _peek(tokens, j)
        next_ident = _peek(tokens, j + 1)
        if not dot or dot.type != "DOT" or not next_ident or next_ident.type != "IDENT":
            break
        parts.append(str(next_ident.value))
        end_tok = next_ident
        consumed += 2
        j += 2
    full_span = TextSpan(tok.line, tok.column, end_tok.line, end_tok.end_column)
    replace_span = TextSpan(end_tok.line, end_tok.column, end_tok.line, end_tok.end_column)
    ref = SymbolReference(
        kind="",
        raw_name=".".join(parts),
        file=Path(),
        span=full_span,
        replace_span=replace_span,
        is_string=False,
    )
    return ref, consumed


def _make_definition(
    kind: str,
    name_tok: TokenSpan,
    module_name: str | None,
    path: Path,
    origin: str,
    exports: Dict[str, ModuleExports],
) -> SymbolDefinition:
    exported = False
    if module_name and module_name in exports:
        exported = exports[module_name].has(kind, str(name_tok.value))
    span = TextSpan(name_tok.line, name_tok.column, name_tok.line, name_tok.end_column)
    return SymbolDefinition(
        kind=kind,
        name=str(name_tok.value),
        module=module_name,
        file=path,
        span=span,
        origin=origin,
        exported=exported,
    )


def _make_reference(kind: str, ref: SymbolReference, path: Path) -> SymbolReference:
    return SymbolReference(
        kind=kind,
        raw_name=ref.raw_name,
        file=path,
        span=ref.span,
        replace_span=ref.replace_span,
        is_string=ref.is_string,
    )


__all__ = [
    "FileIndex",
    "ProjectIndex",
    "SymbolDefinition",
    "SymbolReference",
    "TextSpan",
]
