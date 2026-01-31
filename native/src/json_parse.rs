use std::collections::BTreeMap;

#[derive(Clone, Debug, PartialEq)]
pub enum JsonValue {
    Null,
    Bool(bool),
    Number(i64),
    String(String),
    Array(Vec<JsonValue>),
    Object(BTreeMap<String, JsonValue>),
}

pub fn parse_json(input: &str) -> Result<JsonValue, ()> {
    let mut parser = Parser::new(input);
    let value = parser.parse_value()?;
    parser.skip_ws();
    if parser.peek().is_some() {
        return Err(());
    }
    Ok(value)
}

struct Parser<'a> {
    bytes: &'a [u8],
    pos: usize,
}

impl<'a> Parser<'a> {
    fn new(input: &'a str) -> Self {
        Self {
            bytes: input.as_bytes(),
            pos: 0,
        }
    }

    fn peek(&self) -> Option<u8> {
        self.bytes.get(self.pos).copied()
    }

    fn next(&mut self) -> Option<u8> {
        let value = self.peek()?;
        self.pos += 1;
        Some(value)
    }

    fn skip_ws(&mut self) {
        while let Some(byte) = self.peek() {
            if byte == b' ' || byte == b'\n' || byte == b'\r' || byte == b'\t' {
                self.pos += 1;
            } else {
                break;
            }
        }
    }

    fn parse_value(&mut self) -> Result<JsonValue, ()> {
        self.skip_ws();
        match self.peek() {
            Some(b'n') => self.parse_null(),
            Some(b't') | Some(b'f') => self.parse_bool(),
            Some(b'"') => self.parse_string().map(JsonValue::String),
            Some(b'[') => self.parse_array(),
            Some(b'{') => self.parse_object(),
            Some(b'-') | Some(b'0'..=b'9') => self.parse_number(),
            _ => Err(()),
        }
    }

    fn parse_null(&mut self) -> Result<JsonValue, ()> {
        if self.consume_bytes(b"null") {
            Ok(JsonValue::Null)
        } else {
            Err(())
        }
    }

    fn parse_bool(&mut self) -> Result<JsonValue, ()> {
        if self.consume_bytes(b"true") {
            return Ok(JsonValue::Bool(true));
        }
        if self.consume_bytes(b"false") {
            return Ok(JsonValue::Bool(false));
        }
        Err(())
    }

    fn parse_number(&mut self) -> Result<JsonValue, ()> {
        self.skip_ws();
        let start = self.pos;
        if self.peek() == Some(b'-') {
            self.pos += 1;
        }
        let mut saw_digit = false;
        while let Some(byte) = self.peek() {
            if byte.is_ascii_digit() {
                saw_digit = true;
                self.pos += 1;
            } else {
                break;
            }
        }
        if !saw_digit {
            return Err(());
        }
        if let Some(byte) = self.peek() {
            if byte == b'.' || byte == b'e' || byte == b'E' {
                return Err(());
            }
        }
        let slice = &self.bytes[start..self.pos];
        let text = std::str::from_utf8(slice).map_err(|_| ())?;
        let value = text.parse::<i64>().map_err(|_| ())?;
        Ok(JsonValue::Number(value))
    }

    fn parse_string(&mut self) -> Result<String, ()> {
        if self.next() != Some(b'"') {
            return Err(());
        }
        let mut out = String::new();
        while let Some(byte) = self.next() {
            match byte {
                b'"' => return Ok(out),
                b'\\' => {
                    let escaped = self.next().ok_or(())?;
                    match escaped {
                        b'"' => out.push('"'),
                        b'\\' => out.push('\\'),
                        b'/' => out.push('/'),
                        b'b' => out.push('\u{0008}'),
                        b'f' => out.push('\u{000C}'),
                        b'n' => out.push('\n'),
                        b'r' => out.push('\r'),
                        b't' => out.push('\t'),
                        b'u' => {
                            let code = self.parse_hex_u16()?;
                            let ch = std::char::from_u32(code as u32).ok_or(())?;
                            out.push(ch);
                        }
                        _ => return Err(()),
                    }
                }
                _ => out.push(byte as char),
            }
        }
        Err(())
    }

    fn parse_hex_u16(&mut self) -> Result<u16, ()> {
        let mut value: u16 = 0;
        for _ in 0..4 {
            let byte = self.next().ok_or(())?;
            let digit = match byte {
                b'0'..=b'9' => (byte - b'0') as u16,
                b'a'..=b'f' => (byte - b'a' + 10) as u16,
                b'A'..=b'F' => (byte - b'A' + 10) as u16,
                _ => return Err(()),
            };
            value = (value << 4) | digit;
        }
        Ok(value)
    }

    fn parse_array(&mut self) -> Result<JsonValue, ()> {
        if self.next() != Some(b'[') {
            return Err(());
        }
        let mut items = Vec::new();
        loop {
            self.skip_ws();
            if self.peek() == Some(b']') {
                self.pos += 1;
                break;
            }
            let value = self.parse_value()?;
            items.push(value);
            self.skip_ws();
            match self.next() {
                Some(b',') => continue,
                Some(b']') => break,
                _ => return Err(()),
            }
        }
        Ok(JsonValue::Array(items))
    }

    fn parse_object(&mut self) -> Result<JsonValue, ()> {
        if self.next() != Some(b'{') {
            return Err(());
        }
        let mut map = BTreeMap::new();
        loop {
            self.skip_ws();
            if self.peek() == Some(b'}') {
                self.pos += 1;
                break;
            }
            let key = self.parse_string()?;
            self.skip_ws();
            if self.next() != Some(b':') {
                return Err(());
            }
            let value = self.parse_value()?;
            map.insert(key, value);
            self.skip_ws();
            match self.next() {
                Some(b',') => continue,
                Some(b'}') => break,
                _ => return Err(()),
            }
        }
        Ok(JsonValue::Object(map))
    }

    fn consume_bytes(&mut self, target: &[u8]) -> bool {
        if self.bytes.len() < self.pos + target.len() {
            return false;
        }
        if &self.bytes[self.pos..self.pos + target.len()] != target {
            return false;
        }
        self.pos += target.len();
        true
    }
}
