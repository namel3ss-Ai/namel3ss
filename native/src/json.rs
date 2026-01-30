use core::fmt::Write;

pub fn push_json_string(out: &mut String, value: &str) {
    out.push('"');
    escape_json_string(out, value);
    out.push('"');
}

pub fn escape_json_string(out: &mut String, value: &str) {
    for ch in value.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{0008}' => out.push_str("\\b"),
            '\u{000C}' => out.push_str("\\f"),
            ch if ch.is_ascii() && ch < ' ' => {
                let _ = write!(out, "\\u{:04x}", ch as u32);
            }
            ch if ch.is_ascii() => out.push(ch),
            ch => {
                let mut buf = [0u16; 2];
                for unit in ch.encode_utf16(&mut buf) {
                    let _ = write!(out, "\\u{:04x}", unit);
                }
            }
        }
    }
}
