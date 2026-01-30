use crate::json::push_json_string;

const ESCAPED_IDENTIFIER: &str = "IDENT_ESCAPED";

#[derive(Clone, Debug)]
pub struct Token {
    pub token_type: &'static str,
    pub value: Option<String>,
    pub line: usize,
    pub column: usize,
    pub escaped: bool,
}

#[derive(Debug)]
pub enum ScanError {
    Invalid,
}

pub fn scan(source: &str) -> Result<Vec<Token>, ScanError> {
    let lines = split_lines(source);
    let mut tokens: Vec<Token> = Vec::new();
    let mut indent_stack: Vec<usize> = vec![0];

    for (line_index, raw_line) in lines.iter().enumerate() {
        let line_no = line_index + 1;
        if raw_line.trim().is_empty() {
            continue;
        }
        if raw_line.trim_start().starts_with('#') {
            continue;
        }
        let indent = leading_spaces(raw_line);
        if indent > *indent_stack.last().unwrap_or(&0) {
            tokens.push(Token {
                token_type: "INDENT",
                value: None,
                line: line_no,
                column: 1,
                escaped: false,
            });
            indent_stack.push(indent);
        } else {
            while indent < *indent_stack.last().unwrap_or(&0) {
                indent_stack.pop();
                tokens.push(Token {
                    token_type: "DEDENT",
                    value: None,
                    line: line_no,
                    column: 1,
                    escaped: false,
                });
            }
            if indent != *indent_stack.last().unwrap_or(&0) {
                return Err(ScanError::Invalid);
            }
        }

        let trimmed = lstrip_spaces(raw_line);
        let mut line_tokens = scan_line(trimmed, line_no, indent + 1)?;
        tokens.append(&mut line_tokens);
        let column = raw_line.chars().count() + 1;
        tokens.push(Token {
            token_type: "NEWLINE",
            value: None,
            line: line_no,
            column,
            escaped: false,
        });
    }

    while indent_stack.len() > 1 {
        indent_stack.pop();
        tokens.push(Token {
            token_type: "DEDENT",
            value: None,
            line: lines.len(),
            column: 1,
            escaped: false,
        });
    }

    tokens.push(Token {
        token_type: "EOF",
        value: None,
        line: lines.len() + 1,
        column: 1,
        escaped: false,
    });

    Ok(tokens)
}

pub fn tokens_to_json(tokens: &[Token]) -> Vec<u8> {
    let mut out = String::new();
    out.push('[');
    for (idx, token) in tokens.iter().enumerate() {
        if idx > 0 {
            out.push(',');
        }
        out.push('{');
        out.push_str("\"column\":");
        out.push_str(&token.column.to_string());
        out.push_str(",\"escaped\":");
        out.push_str(if token.escaped { "true" } else { "false" });
        out.push_str(",\"line\":");
        out.push_str(&token.line.to_string());
        out.push_str(",\"type\":");
        push_json_string(&mut out, token.token_type);
        out.push_str(",\"value\":");
        match &token.value {
            Some(value) => push_json_string(&mut out, value),
            None => out.push_str("null"),
        }
        out.push('}');
    }
    out.push(']');
    out.into_bytes()
}

fn scan_line(text: &str, line_no: usize, start_col: usize) -> Result<Vec<Token>, ScanError> {
    let chars: Vec<char> = text.chars().collect();
    let mut tokens: Vec<Token> = Vec::new();
    let mut i = 0usize;
    let mut column = start_col;
    while i < chars.len() {
        let ch = chars[i];
        if ch == ' ' {
            i += 1;
            column += 1;
            continue;
        }
        match ch {
            ':' => {
                tokens.push(simple_token("COLON", ":", line_no, column));
                i += 1;
                column += 1;
            }
            '.' => {
                tokens.push(simple_token("DOT", ".", line_no, column));
                i += 1;
                column += 1;
            }
            '+' => {
                tokens.push(simple_token("PLUS", "+", line_no, column));
                i += 1;
                column += 1;
            }
            '-' => {
                tokens.push(simple_token("MINUS", "-", line_no, column));
                i += 1;
                column += 1;
            }
            '*' => {
                if i + 1 < chars.len() && chars[i + 1] == '*' {
                    tokens.push(simple_token("POWER", "**", line_no, column));
                    i += 2;
                    column += 2;
                } else {
                    tokens.push(simple_token("STAR", "*", line_no, column));
                    i += 1;
                    column += 1;
                }
            }
            '/' => {
                tokens.push(simple_token("SLASH", "/", line_no, column));
                i += 1;
                column += 1;
            }
            '%' => {
                tokens.push(simple_token("PERCENT", "%", line_no, column));
                i += 1;
                column += 1;
            }
            '=' => {
                tokens.push(simple_token("EQUALS", "=", line_no, column));
                i += 1;
                column += 1;
            }
            '(' => {
                tokens.push(simple_token("LPAREN", "(", line_no, column));
                i += 1;
                column += 1;
            }
            ')' => {
                tokens.push(simple_token("RPAREN", ")", line_no, column));
                i += 1;
                column += 1;
            }
            '[' => {
                tokens.push(simple_token("LBRACKET", "[", line_no, column));
                i += 1;
                column += 1;
            }
            ']' => {
                tokens.push(simple_token("RBRACKET", "]", line_no, column));
                i += 1;
                column += 1;
            }
            ',' => {
                tokens.push(simple_token("COMMA", ",", line_no, column));
                i += 1;
                column += 1;
            }
            '`' => {
                let (value, consumed) = read_escaped_identifier(&chars, i)?;
                tokens.push(Token {
                    token_type: ESCAPED_IDENTIFIER,
                    value: Some(value),
                    line: line_no,
                    column,
                    escaped: true,
                });
                i += consumed;
                column += consumed;
            }
            '"' => {
                let (value, consumed) = read_string(&chars, i)?;
                tokens.push(Token {
                    token_type: "STRING",
                    value: Some(value),
                    line: line_no,
                    column,
                    escaped: false,
                });
                i += consumed;
                column += consumed;
            }
            ch if ch.is_digit(10) => {
                let (value, consumed) = read_number(&chars, i);
                tokens.push(Token {
                    token_type: "NUMBER",
                    value: Some(value),
                    line: line_no,
                    column,
                    escaped: false,
                });
                i += consumed;
                column += consumed;
            }
            ch if ch.is_alphabetic() || ch == '_' => {
                let (value, consumed) = read_identifier(&chars, i);
                let token_type = keyword_token_type(&value).unwrap_or("IDENT");
                tokens.push(Token {
                    token_type,
                    value: Some(value),
                    line: line_no,
                    column,
                    escaped: false,
                });
                i += consumed;
                column += consumed;
            }
            '{' | '}' => return Err(ScanError::Invalid),
            _ => return Err(ScanError::Invalid),
        }
    }
    Ok(tokens)
}

fn read_string(chars: &[char], start: usize) -> Result<(String, usize), ScanError> {
    let mut i = start + 1;
    let mut value = String::new();
    while i < chars.len() {
        if chars[i] == '"' {
            return Ok((value, i - start + 1));
        }
        value.push(chars[i]);
        i += 1;
    }
    Err(ScanError::Invalid)
}

fn read_number(chars: &[char], start: usize) -> (String, usize) {
    let mut i = start;
    let mut value = String::new();
    while i < chars.len() && chars[i].is_digit(10) {
        value.push(chars[i]);
        i += 1;
    }
    if i + 1 < chars.len() && chars[i] == '.' && chars[i + 1].is_digit(10) {
        value.push('.');
        i += 1;
        while i < chars.len() && chars[i].is_digit(10) {
            value.push(chars[i]);
            i += 1;
        }
    }
    (value, i - start)
}

fn read_identifier(chars: &[char], start: usize) -> (String, usize) {
    let mut i = start;
    let mut value = String::new();
    while i < chars.len() && (chars[i].is_alphanumeric() || chars[i] == '_') {
        value.push(chars[i]);
        i += 1;
    }
    (value, i - start)
}

fn read_escaped_identifier(chars: &[char], start: usize) -> Result<(String, usize), ScanError> {
    let mut i = start + 1;
    while i < chars.len() {
        if chars[i] == '`' {
            let value: String = chars[start + 1..i].iter().collect();
            if value.is_empty() {
                return Err(ScanError::Invalid);
            }
            if !is_identifier_text(&value) {
                return Err(ScanError::Invalid);
            }
            return Ok((value, i - start + 1));
        }
        i += 1;
    }
    Err(ScanError::Invalid)
}

fn is_identifier_text(value: &str) -> bool {
    let mut chars = value.chars();
    let first = match chars.next() {
        Some(ch) => ch,
        None => return false,
    };
    if !(first.is_alphabetic() || first == '_') {
        return false;
    }
    for ch in chars {
        if !(ch.is_alphanumeric() || ch == '_') {
            return false;
        }
    }
    true
}

fn simple_token(token_type: &'static str, value: &'static str, line: usize, column: usize) -> Token {
    Token {
        token_type,
        value: Some(value.to_string()),
        line,
        column,
        escaped: false,
    }
}

fn leading_spaces(text: &str) -> usize {
    text.chars().take_while(|ch| *ch == ' ').count()
}

fn lstrip_spaces(text: &str) -> &str {
    let mut idx = text.len();
    for (offset, ch) in text.char_indices() {
        if ch != ' ' {
            idx = offset;
            break;
        }
    }
    if idx == text.len() {
        return "";
    }
    &text[idx..]
}

fn split_lines(source: &str) -> Vec<&str> {
    if source.is_empty() {
        return Vec::new();
    }
    let mut lines: Vec<&str> = Vec::new();
    let mut start = 0usize;
    let mut iter = source.char_indices().peekable();
    while let Some((idx, ch)) = iter.next() {
        if ch == '\r' {
            lines.push(&source[start..idx]);
            if let Some(&(_, next)) = iter.peek() {
                if next == '\n' {
                    iter.next();
                }
            }
            start = iter.peek().map(|(pos, _)| *pos).unwrap_or(source.len());
            continue;
        }
        if is_line_break(ch) {
            lines.push(&source[start..idx]);
            start = idx + ch.len_utf8();
        }
    }
    if start < source.len() {
        lines.push(&source[start..]);
    }
    lines
}

fn is_line_break(ch: char) -> bool {
    matches!(
        ch,
        '\n'
            | '\u{000B}'
            | '\u{000C}'
            | '\u{001C}'
            | '\u{001D}'
            | '\u{001E}'
            | '\u{0085}'
            | '\u{2028}'
            | '\u{2029}'
    )
}

fn keyword_token_type(value: &str) -> Option<&'static str> {
    match value {
        "flow" => Some("FLOW"),
        "page" => Some("PAGE"),
        "app" => Some("APP"),
        "spec" => Some("SPEC"),
        "ai" => Some("AI"),
        "ask" => Some("ASK"),
        "with" => Some("WITH"),
        "input" => Some("INPUT"),
        "input_schema" => Some("INPUT_SCHEMA"),
        "output_schema" => Some("OUTPUT_SCHEMA"),
        "as" => Some("AS"),
        "provider" => Some("PROVIDER"),
        "tools" => Some("TOOLS"),
        "expose" => Some("EXPOSE"),
        "tool" => Some("TOOL"),
        "call" => Some("CALL"),
        "kind" => Some("KIND"),
        "entry" => Some("ENTRY"),
        "purity" => Some("PURITY"),
        "timeout_seconds" => Some("TIMEOUT_SECONDS"),
        "memory" => Some("MEMORY"),
        "short_term" => Some("SHORT_TERM"),
        "semantic" => Some("SEMANTIC"),
        "profile" => Some("PROFILE"),
        "agent" => Some("AGENT"),
        "agents" => Some("AGENTS"),
        "parallel" => Some("PARALLEL"),
        "run" => Some("RUN"),
        "model" => Some("MODEL"),
        "system_prompt" => Some("SYSTEM_PROMPT"),
        "title" => Some("TITLE"),
        "text" => Some("TEXT"),
        "theme" => Some("THEME"),
        "theme_tokens" => Some("THEME_TOKENS"),
        "theme_preference" => Some("THEME_PREFERENCE"),
        "ui" => Some("UI"),
        "form" => Some("FORM"),
        "table" => Some("TABLE"),
        "button" => Some("BUTTON"),
        "section" => Some("SECTION"),
        "card" => Some("CARD"),
        "row" => Some("ROW"),
        "column" => Some("COLUMN"),
        "divider" => Some("DIVIDER"),
        "image" => Some("IMAGE"),
        "calls" => Some("CALLS"),
        "record" => Some("RECORD"),
        "save" => Some("SAVE"),
        "create" => Some("CREATE"),
        "find" => Some("FIND"),
        "where" => Some("WHERE"),
        "let" => Some("LET"),
        "latest" => Some("LATEST"),
        "set" => Some("SET"),
        "require" => Some("REQUIRE"),
        "return" => Some("RETURN"),
        "repeat" => Some("REPEAT"),
        "up" => Some("UP"),
        "to" => Some("TO"),
        "times" => Some("TIMES"),
        "for" => Some("FOR"),
        "each" => Some("EACH"),
        "in" => Some("IN"),
        "match" => Some("MATCH"),
        "when" => Some("WHEN"),
        "otherwise" => Some("OTHERWISE"),
        "try" => Some("TRY"),
        "catch" => Some("CATCH"),
        "if" => Some("IF"),
        "else" => Some("ELSE"),
        "is" => Some("IS"),
        "greater" => Some("GREATER"),
        "less" => Some("LESS"),
        "equal" => Some("EQUAL"),
        "than" => Some("THAN"),
        "and" => Some("AND"),
        "or" => Some("OR"),
        "not" => Some("NOT"),
        "state" => Some("STATE"),
        "constant" => Some("CONSTANT"),
        "true" => Some("BOOLEAN"),
        "false" => Some("BOOLEAN"),
        "null" => Some("NULL"),
        "string" => Some("TYPE_STRING"),
        "str" => Some("TYPE_STRING"),
        "int" => Some("TYPE_INT"),
        "integer" => Some("TYPE_INT"),
        "number" => Some("TYPE_NUMBER"),
        "boolean" => Some("TYPE_BOOLEAN"),
        "bool" => Some("TYPE_BOOLEAN"),
        "json" => Some("TYPE_JSON"),
        "must" => Some("MUST"),
        "be" => Some("BE"),
        "present" => Some("PRESENT"),
        "unique" => Some("UNIQUE"),
        "pattern" => Some("PATTERN"),
        "param" => Some("PARAM"),
        "have" => Some("HAVE"),
        "length" => Some("LENGTH"),
        "at" => Some("AT"),
        "least" => Some("LEAST"),
        "most" => Some("MOST"),
        "capabilities" => Some("CAPABILITIES"),
        "job" => Some("JOB"),
        "enqueue" => Some("ENQUEUE"),
        _ => None,
    }
}
