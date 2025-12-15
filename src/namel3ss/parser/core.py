from __future__ import annotations
from typing import List
from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.lexer.lexer import Lexer
from namel3ss.lexer.tokens import Token
from namel3ss.parser.ai import parse_ai_decl, parse_ask_stmt
from namel3ss.parser.tool import parse_tool
from namel3ss.parser.agent import parse_agent_decl, parse_run_agent_stmt, parse_run_agents_parallel
class Parser:
    def __init__(self, tokens: List[Token]) -> None:
        self.tokens = tokens
        self.position = 0
    @classmethod
    def parse(cls, source: str) -> ast.Program:
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = cls(tokens)
        program = parser._parse_program()
        parser._expect("EOF")
        return program
    def _current(self) -> Token:
        return self.tokens[self.position]
    def _advance(self) -> Token:
        tok = self.tokens[self.position]
        self.position += 1
        return tok
    def _match(self, *types: str) -> bool:
        if self._current().type in types:
            self._advance()
            return True
        return False
    def _expect(self, token_type: str, message: str | None = None) -> Token:
        tok = self._current()
        if tok.type != token_type:
            raise Namel3ssError(
                message or f"Expected {token_type}, got {tok.type}",
                line=tok.line,
                column=tok.column,
            )
        self._advance()
        return tok
    def _parse_program(self) -> ast.Program:
        records: List[ast.RecordDecl] = []
        flows: List[ast.Flow] = []
        pages: List[ast.PageDecl] = []
        ais: List[ast.AIDecl] = []
        tools: List[ast.ToolDecl] = []
        agents: List[ast.AgentDecl] = []
        while self._current().type != "EOF":
            if self._match("NEWLINE"):
                continue
            if self._current().type == "TOOL":
                tools.append(parse_tool(self))
                continue
            if self._current().type == "AGENT":
                agents.append(parse_agent_decl(self))
                continue
            if self._current().type == "AI":
                ais.append(parse_ai_decl(self))
                continue
            if self._current().type == "RECORD":
                records.append(self._parse_record())
                continue
            if self._current().type == "FLOW":
                flows.append(self._parse_flow())
                continue
            if self._current().type == "PAGE":
                pages.append(self._parse_page())
                continue
            tok = self._current()
            raise Namel3ssError("Unexpected top-level token", line=tok.line, column=tok.column)
        return ast.Program(records=records, flows=flows, pages=pages, ais=ais, tools=tools, agents=agents, line=None, column=None)
    def _parse_flow(self) -> ast.Flow:
        flow_tok = self._expect("FLOW", "Expected 'flow' declaration")
        name_tok = self._expect("STRING", "Expected flow name string")
        self._expect("COLON", "Expected ':' after flow name")
        self._expect("NEWLINE", "Expected newline after flow header")
        self._expect("INDENT", "Expected indented block for flow body")
        body = self._parse_statements(until={"DEDENT"})
        self._expect("DEDENT", "Expected block end")
        while self._match("NEWLINE"):
            pass
        return ast.Flow(name=name_tok.value, body=body, line=flow_tok.line, column=flow_tok.column)
    def _parse_statements(self, until: set[str]) -> List[ast.Statement]:
        statements: List[ast.Statement] = []
        while self._current().type not in until:
            if self._match("NEWLINE"):
                continue
            statements.append(self._parse_statement())
        return statements
    def _parse_statement(self) -> ast.Statement:
        tok = self._current()
        if tok.type == "LET":
            return self._parse_let()
        if tok.type == "SET":
            return self._parse_set()
        if tok.type == "IF":
            return self._parse_if()
        if tok.type == "RETURN":
            return self._parse_return()
        if tok.type == "ASK":
            return parse_ask_stmt(self)
        if tok.type == "RUN":
            next_type = self.tokens[self.position + 1].type
            if next_type == "AGENT":
                return parse_run_agent_stmt(self)
            if next_type == "AGENTS":
                return parse_run_agents_parallel(self)
            raise Namel3ssError("Expected 'agent' or 'agents' after run", line=tok.line, column=tok.column)
        if tok.type == "REPEAT":
            return self._parse_repeat()
        if tok.type == "FOR":
            return self._parse_for_each()
        if tok.type == "MATCH":
            return self._parse_match()
        if tok.type == "TRY":
            return self._parse_try()
        if tok.type == "SAVE":
            return self._parse_save()
        if tok.type == "FIND":
            return self._parse_find()
        raise Namel3ssError(f"Unexpected token '{tok.type}' in statement", line=tok.line, column=tok.column)
    def _parse_let(self) -> ast.Let:
        let_tok = self._advance()
        name_tok = self._expect("IDENT", "Expected identifier after 'let'")
        self._expect("IS", "Expected 'is' in declaration")
        expr = self._parse_expression()
        constant = False
        if self._match("CONSTANT"):
            constant = True
        return ast.Let(name=name_tok.value, expression=expr, constant=constant, line=let_tok.line, column=let_tok.column)
    def _parse_set(self) -> ast.Set:
        set_tok = self._advance()
        target = self._parse_target()
        self._expect("IS", "Expected 'is' in assignment")
        expr = self._parse_expression()
        return ast.Set(target=target, expression=expr, line=set_tok.line, column=set_tok.column)
    def _parse_target(self) -> ast.Assignable:
        tok = self._current()
        if tok.type == "STATE":
            return self._parse_state_path()
        if tok.type == "IDENT":
            name_tok = self._advance()
            return ast.VarReference(name=name_tok.value, line=name_tok.line, column=name_tok.column)
        raise Namel3ssError("Expected assignment target", line=tok.line, column=tok.column)
    def _parse_if(self) -> ast.If:
        if_tok = self._advance()
        condition = self._parse_expression()
        self._expect("COLON", "Expected ':' after condition")
        self._expect("NEWLINE", "Expected newline after condition")
        self._expect("INDENT", "Expected indented block for if body")
        then_body = self._parse_statements(until={"DEDENT"})
        self._expect("DEDENT", "Expected block end")
        else_body: List[ast.Statement] = []
        while self._match("NEWLINE"):
            pass
        if self._match("ELSE"):
            self._expect("COLON", "Expected ':' after else")
            self._expect("NEWLINE", "Expected newline after else")
            self._expect("INDENT", "Expected indented block for else body")
            else_body = self._parse_statements(until={"DEDENT"})
            self._expect("DEDENT", "Expected block end")
            while self._match("NEWLINE"):
                pass
        return ast.If(
            condition=condition,
            then_body=then_body,
            else_body=else_body,
            line=if_tok.line,
            column=if_tok.column,
        )
    def _parse_return(self) -> ast.Return:
        ret_tok = self._advance()
        expr = self._parse_expression()
        return ast.Return(expression=expr, line=ret_tok.line, column=ret_tok.column)
    def _parse_repeat(self) -> ast.Repeat:
        rep_tok = self._advance()
        self._expect("UP", "Expected 'up' in repeat statement")
        self._expect("TO", "Expected 'to' in repeat statement")
        count_expr = self._parse_expression()
        self._expect("TIMES", "Expected 'times' after repeat count")
        self._expect("COLON", "Expected ':' after repeat header")
        body = self._parse_block()
        return ast.Repeat(count=count_expr, body=body, line=rep_tok.line, column=rep_tok.column)
    def _parse_for_each(self) -> ast.ForEach:
        for_tok = self._advance()
        self._expect("EACH", "Expected 'each' after 'for'")
        name_tok = self._expect("IDENT", "Expected loop variable name")
        self._expect("IN", "Expected 'in' in for-each loop")
        iterable = self._parse_expression()
        self._expect("COLON", "Expected ':' after for-each header")
        body = self._parse_block()
        return ast.ForEach(name=name_tok.value, iterable=iterable, body=body, line=for_tok.line, column=for_tok.column)
    def _parse_match(self) -> ast.Match:
        match_tok = self._advance()
        expr = self._parse_expression()
        self._expect("COLON", "Expected ':' after match expression")
        self._expect("NEWLINE", "Expected newline after match header")
        self._expect("INDENT", "Expected indented match body")
        self._expect("WITH", "Expected 'with' inside match")
        self._expect("COLON", "Expected ':' after 'with'")
        self._expect("NEWLINE", "Expected newline after 'with:'")
        self._expect("INDENT", "Expected indented match cases")
        cases: List[ast.MatchCase] = []
        otherwise_body: List[ast.Statement] | None = None
        while self._current().type not in {"DEDENT"}:
            if self._match("WHEN"):
                pattern_expr = self._parse_expression()
                self._validate_match_pattern(pattern_expr)
                self._expect("COLON", "Expected ':' after when pattern")
                case_body = self._parse_block()
                if otherwise_body is not None:
                    raise Namel3ssError("Unreachable case after otherwise", line=pattern_expr.line, column=pattern_expr.column)
                cases.append(ast.MatchCase(pattern=pattern_expr, body=case_body, line=pattern_expr.line, column=pattern_expr.column))
                continue
            if self._match("OTHERWISE"):
                if otherwise_body is not None:
                    tok = self.tokens[self.position - 1]
                    raise Namel3ssError("Duplicate otherwise in match", line=tok.line, column=tok.column)
                self._expect("COLON", "Expected ':' after otherwise")
                otherwise_body = self._parse_block()
                continue
            tok = self._current()
            raise Namel3ssError("Expected 'when' or 'otherwise' in match", line=tok.line, column=tok.column)
        self._expect("DEDENT", "Expected end of match cases")
        self._expect("DEDENT", "Expected end of match block")
        while self._match("NEWLINE"):
            pass
        if not cases and otherwise_body is None:
            raise Namel3ssError("Match must have at least one case", line=match_tok.line, column=match_tok.column)
        return ast.Match(expression=expr, cases=cases, otherwise=otherwise_body, line=match_tok.line, column=match_tok.column)
    def _parse_try(self) -> ast.TryCatch:
        try_tok = self._advance()
        self._expect("COLON", "Expected ':' after try")
        try_body = self._parse_block()
        if not self._match("WITH"):
            tok = self._current()
            raise Namel3ssError("Expected 'with' introducing catch", line=tok.line, column=tok.column)
        self._expect("CATCH", "Expected 'catch' after 'with'")
        var_tok = self._expect("IDENT", "Expected catch variable name")
        self._expect("COLON", "Expected ':' after catch clause")
        catch_body = self._parse_block()
        return ast.TryCatch(try_body=try_body, catch_var=var_tok.value, catch_body=catch_body, line=try_tok.line, column=try_tok.column)
    def _parse_save(self) -> ast.Save:
        tok = self._advance()
        name_tok = self._expect("IDENT", "Expected record name after 'save'")
        return ast.Save(record_name=name_tok.value, line=tok.line, column=tok.column)
    def _parse_find(self) -> ast.Find:
        tok = self._advance()
        name_tok = self._expect("IDENT", "Expected record name after 'find'")
        self._expect("WHERE", "Expected 'where' in find statement")
        predicate = self._parse_expression()
        return ast.Find(record_name=name_tok.value, predicate=predicate, line=tok.line, column=tok.column)
    def _validate_match_pattern(self, pattern: ast.Expression) -> None:
        if isinstance(pattern, (ast.Literal, ast.VarReference, ast.StatePath)):
            return
        raise Namel3ssError("Match patterns must be literal or identifier", line=pattern.line, column=pattern.column)
    def _parse_block(self) -> List[ast.Statement]:
        self._expect("NEWLINE", "Expected newline before block")
        self._expect("INDENT", "Expected indented block")
        stmts = self._parse_statements(until={"DEDENT"})
        self._expect("DEDENT", "Expected end of block")
        while self._match("NEWLINE"):
            pass
        return stmts
    def _parse_expression(self) -> ast.Expression:
        return self._parse_or()
    def _parse_or(self) -> ast.Expression:
        expr = self._parse_and()
        while self._match("OR"):
            op_tok = self.tokens[self.position - 1]
            right = self._parse_and()
            expr = ast.BinaryOp(op="or", left=expr, right=right, line=op_tok.line, column=op_tok.column)
        return expr
    def _parse_and(self) -> ast.Expression:
        expr = self._parse_not()
        while self._match("AND"):
            op_tok = self.tokens[self.position - 1]
            right = self._parse_not()
            expr = ast.BinaryOp(op="and", left=expr, right=right, line=op_tok.line, column=op_tok.column)
        return expr
    def _parse_not(self) -> ast.Expression:
        if self._match("NOT"):
            tok = self.tokens[self.position - 1]
            operand = self._parse_not()
            return ast.UnaryOp(op="not", operand=operand, line=tok.line, column=tok.column)
        return self._parse_comparison()
    def _parse_comparison(self) -> ast.Expression:
        left = self._parse_primary()
        if not self._match("IS"):
            return left
        is_tok = self.tokens[self.position - 1]
        if self._match("GREATER"):
            self._expect("THAN", "Expected 'than' after 'is greater'")
            right = self._parse_primary()
            return ast.Comparison(kind="gt", left=left, right=right, line=is_tok.line, column=is_tok.column)
        if self._match("LESS"):
            self._expect("THAN", "Expected 'than' after 'is less'")
            right = self._parse_primary()
            return ast.Comparison(kind="lt", left=left, right=right, line=is_tok.line, column=is_tok.column)
        if self._match("EQUAL"):
            if self._match("TO"):
                pass
            right = self._parse_primary()
            return ast.Comparison(kind="eq", left=left, right=right, line=is_tok.line, column=is_tok.column)
        right = self._parse_primary()
        return ast.Comparison(kind="eq", left=left, right=right, line=is_tok.line, column=is_tok.column)
    def _parse_primary(self) -> ast.Expression:
        tok = self._current()
        if tok.type == "NUMBER":
            self._advance()
            return ast.Literal(value=tok.value, line=tok.line, column=tok.column)
        if tok.type == "STRING":
            self._advance()
            return ast.Literal(value=tok.value, line=tok.line, column=tok.column)
        if tok.type == "BOOLEAN":
            self._advance()
            return ast.Literal(value=tok.value, line=tok.line, column=tok.column)
        if tok.type in {"IDENT", "INPUT"}:
            self._advance()
            attrs: List[str] = []
            while self._match("DOT"):
                attr_tok = self._expect("IDENT", "Expected identifier after '.'")
                attrs.append(attr_tok.value)
            if attrs:
                return ast.AttrAccess(base=tok.value, attrs=attrs, line=tok.line, column=tok.column)
            return ast.VarReference(name=tok.value, line=tok.line, column=tok.column)
        if tok.type == "STATE":
            return self._parse_state_path()
        if tok.type == "LPAREN":
            self._advance()
            expr = self._parse_expression()
            self._expect("RPAREN", "Expected ')'")
            return expr
        if tok.type == "ASK":
            raise Namel3ssError(
                'AI calls are statements. Use: ask ai "name" with input: <expr> as <target>.',
                line=tok.line,
                column=tok.column,
            )
        raise Namel3ssError("Unexpected expression", line=tok.line, column=tok.column)
    def _parse_state_path(self) -> ast.StatePath:
        state_tok = self._expect("STATE", "Expected 'state'")
        path: List[str] = []
        while self._match("DOT"):
            ident_tok = self._expect("IDENT", "Expected identifier after '.'")
            path.append(ident_tok.value)
        if not path:
            raise Namel3ssError("Expected state path after 'state'", line=state_tok.line, column=state_tok.column)
        return ast.StatePath(path=path, line=state_tok.line, column=state_tok.column)
    def _parse_record(self) -> ast.RecordDecl:
        rec_tok = self._advance()
        name_tok = self._expect("STRING", "Expected record name string")
        self._expect("COLON", "Expected ':' after record name")
        fields = self._parse_record_fields()
        return ast.RecordDecl(name=name_tok.value, fields=fields, line=rec_tok.line, column=rec_tok.column)
    def _parse_page(self) -> ast.PageDecl:
        page_tok = self._advance()
        name_tok = self._expect("STRING", "Expected page name string")
        self._expect("COLON", "Expected ':' after page name")
        self._expect("NEWLINE", "Expected newline after page header")
        self._expect("INDENT", "Expected indented page body")
        items: List[ast.PageItem] = []
        while self._current().type != "DEDENT":
            if self._match("NEWLINE"):
                continue
            items.append(self._parse_page_item())
        self._expect("DEDENT", "Expected end of page body")
        return ast.PageDecl(name=name_tok.value, items=items, line=page_tok.line, column=page_tok.column)
    def _parse_page_item(self) -> ast.PageItem:
        tok = self._current()
        if tok.type == "TITLE":
            self._advance()
            self._expect("IS", "Expected 'is' after 'title'")
            value_tok = self._expect("STRING", "Expected title string")
            return ast.TitleItem(value=value_tok.value, line=tok.line, column=tok.column)
        if tok.type == "TEXT":
            self._advance()
            self._expect("IS", "Expected 'is' after 'text'")
            value_tok = self._expect("STRING", "Expected text string")
            return ast.TextItem(value=value_tok.value, line=tok.line, column=tok.column)
        if tok.type == "FORM":
            self._advance()
            self._expect("IS", "Expected 'is' after 'form'")
            value_tok = self._expect("STRING", "Expected form record name")
            return ast.FormItem(record_name=value_tok.value, line=tok.line, column=tok.column)
        if tok.type == "TABLE":
            self._advance()
            self._expect("IS", "Expected 'is' after 'table'")
            value_tok = self._expect("STRING", "Expected table record name")
            return ast.TableItem(record_name=value_tok.value, line=tok.line, column=tok.column)
        if tok.type == "BUTTON":
            self._advance()
            label_tok = self._expect("STRING", "Expected button label string")
            self._expect("CALLS", "Expected 'calls' in button action")
            self._expect("FLOW", "Expected 'flow' keyword in button action")
            flow_tok = self._expect("STRING", "Expected flow name string")
            return ast.ButtonItem(label=label_tok.value, flow_name=flow_tok.value, line=tok.line, column=tok.column)
        raise Namel3ssError(
            f"Pages are declarative; unexpected item '{tok.type.lower()}'",
            line=tok.line,
            column=tok.column,
        )
    def _parse_record_fields(self) -> List[ast.FieldDecl]:
        self._expect("NEWLINE", "Expected newline after record header")
        self._expect("INDENT", "Expected indented record body")
        fields: List[ast.FieldDecl] = []
        while self._current().type != "DEDENT":
            if self._match("NEWLINE"):
                continue
            name_tok = self._current()
            if name_tok.type not in {"IDENT", "TITLE", "TEXT", "FORM", "TABLE", "BUTTON", "PAGE"}:
                raise Namel3ssError("Expected field name", line=name_tok.line, column=name_tok.column)
            self._advance()
            type_tok = self._current()
            if not type_tok.type.startswith("TYPE_"):
                raise Namel3ssError("Expected field type", line=type_tok.line, column=type_tok.column)
            self._advance()
            type_name = self._type_from_token(type_tok)
            constraint = None
            if self._match("MUST"):
                constraint = self._parse_field_constraint()
            fields.append(
                ast.FieldDecl(
                    name=name_tok.value,
                    type_name=type_name,
                    constraint=constraint,
                    line=name_tok.line,
                    column=name_tok.column,
                )
            )
            if self._match("NEWLINE"):
                continue
        self._expect("DEDENT", "Expected end of record body")
        while self._match("NEWLINE"):
            pass
        return fields
    def _parse_field_constraint(self) -> ast.FieldConstraint:
        tok = self._current()
        if self._match("BE"):
            if self._match("PRESENT"):
                return ast.FieldConstraint(kind="present", line=tok.line, column=tok.column)
            if self._match("UNIQUE"):
                return ast.FieldConstraint(kind="unique", line=tok.line, column=tok.column)
            if self._match("GREATER"):
                self._expect("THAN", "Expected 'than' after 'greater'")
                expr = self._parse_expression()
                return ast.FieldConstraint(kind="gt", expression=expr, line=tok.line, column=tok.column)
            if self._match("LESS"):
                self._expect("THAN", "Expected 'than' after 'less'")
                expr = self._parse_expression()
                return ast.FieldConstraint(kind="lt", expression=expr, line=tok.line, column=tok.column)
        if self._match("MATCH"):
            self._expect("PATTERN", "Expected 'pattern'")
            pattern_tok = self._expect("STRING", "Expected pattern string")
            return ast.FieldConstraint(kind="pattern", pattern=pattern_tok.value, line=tok.line, column=tok.column)
        if self._match("HAVE"):
            self._expect("LENGTH", "Expected 'length'")
            self._expect("AT", "Expected 'at'")
            if self._match("LEAST"):
                expr = self._parse_expression()
                return ast.FieldConstraint(kind="len_min", expression=expr, line=tok.line, column=tok.column)
            if self._match("MOST"):
                expr = self._parse_expression()
                return ast.FieldConstraint(kind="len_max", expression=expr, line=tok.line, column=tok.column)
            tok = self._current()
            raise Namel3ssError("Expected 'least' or 'most' after length", line=tok.line, column=tok.column)
        raise Namel3ssError("Unknown constraint", line=tok.line, column=tok.column)
    @staticmethod
    def _type_from_token(tok: Token) -> str:
        if tok.type == "TYPE_STRING":
            return "string"
        if tok.type == "TYPE_INT":
            return "int"
        if tok.type == "TYPE_NUMBER":
            return "number"
        if tok.type == "TYPE_BOOLEAN":
            return "boolean"
        if tok.type == "TYPE_JSON":
            return "json"
        raise Namel3ssError("Invalid type", line=tok.line, column=tok.column)
def parse(source: str) -> ast.Program:
    return Parser.parse(source)
