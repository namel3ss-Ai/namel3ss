use std::collections::{HashMap, HashSet};

pub fn normalize_text(text: &str) -> String {
    if text.is_empty() {
        return String::new();
    }
    let cleaned = text.replace("\r\n", "\n").replace('\r', "\n");
    let cleaned = remove_hyphen_breaks(&cleaned);
    let cleaned = suppress_headers_footers(&cleaned);
    let cleaned = cleaned.replace('\u{000C}', "\n");
    let mut lines = Vec::new();
    for line in cleaned.split('\n') {
        let collapsed = line.split_whitespace().collect::<Vec<_>>().join(" ");
        lines.push(collapsed);
    }
    let cleaned = lines.join("\n");
    let cleaned = collapse_blank_lines(&cleaned);
    cleaned.trim().to_string()
}

fn remove_hyphen_breaks(text: &str) -> String {
    let chars: Vec<char> = text.chars().collect();
    let mut out = String::with_capacity(chars.len());
    let mut i = 0;
    while i < chars.len() {
        if chars[i] == '-'
            && i + 2 < chars.len()
            && chars[i + 1] == '\\\\'
            && chars[i + 2] == 'n'
            && i >= 2
            && chars[i - 2] == '\\\\'
            && chars[i - 1] == 'w'
            && i + 4 < chars.len()
            && chars[i + 3] == '\\\\'
            && chars[i + 4] == 'w'
        {
            i += 3;
            continue;
        }
        out.push(chars[i]);
        i += 1;
    }
    out
}

fn suppress_headers_footers(text: &str) -> String {
    if !text.contains('\u{000C}') {
        return text.to_string();
    }
    let pages: Vec<&str> = text.split('\u{000C}').collect();
    if pages.len() <= 1 {
        return text.to_string();
    }
    let headers = common_edge_lines(&pages, Position::Start);
    let footers = common_edge_lines(&pages, Position::End);
    let mut cleaned_pages = Vec::new();
    for page in pages {
        let mut lines: Vec<&str> = page.lines().collect();
        while !lines.is_empty() && headers.contains(lines[0].trim()) {
            lines.remove(0);
        }
        while !lines.is_empty() && footers.contains(lines[lines.len() - 1].trim()) {
            lines.pop();
        }
        cleaned_pages.push(lines.join("\n"));
    }
    cleaned_pages.join("\u{000C}")
}

fn common_edge_lines(pages: &[&str], position: Position) -> HashSet<String> {
    let mut counts: HashMap<String, usize> = HashMap::new();
    for page in pages {
        let mut lines: Vec<&str> = page.lines().collect();
        lines.retain(|line| !line.trim().is_empty());
        if lines.is_empty() {
            continue;
        }
        let edge = match position {
            Position::Start => lines[0].trim(),
            Position::End => lines[lines.len() - 1].trim(),
        };
        *counts.entry(edge.to_string()).or_insert(0) += 1;
    }
    let threshold = std::cmp::max(2, pages.len() / 2 + 1);
    counts
        .into_iter()
        .filter_map(|(line, count)| if count >= threshold { Some(line) } else { None })
        .collect()
}

fn collapse_blank_lines(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    let mut newline_count = 0;
    for ch in text.chars() {
        if ch == '\n' {
            newline_count += 1;
            if newline_count <= 2 {
                out.push(ch);
            }
            continue;
        }
        newline_count = 0;
        out.push(ch);
    }
    out
}

#[derive(Copy, Clone)]
enum Position {
    Start,
    End,
}
