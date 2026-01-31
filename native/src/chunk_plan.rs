const REASON_SEGMENT: u32 = 1;
const SCORE_DEFAULT: u32 = 0;

pub struct ChunkPlan {
    pub max_chars: u32,
    pub overlap: u32,
    pub chunks: Vec<ChunkEntry>,
}

pub struct ChunkEntry {
    pub index: u32,
    pub paragraph_index: u32,
    pub start: u32,
    pub length: u32,
    pub chars: u32,
    pub reason_code: u32,
    pub score: u32,
}

pub fn plan_chunks(text: &str, max_chars: u32, overlap: u32) -> ChunkPlan {
    let max_chars_usize = max_chars as usize;
    let overlap_usize = overlap as usize;
    let effective_overlap = effective_overlap(max_chars_usize, overlap_usize) as u32;
    let mut chunks = Vec::new();
    if text.is_empty() {
        return ChunkPlan {
            max_chars,
            overlap: effective_overlap,
            chunks,
        };
    }
    let paragraphs: Vec<String> = text
        .split("\n\n")
        .filter_map(|part| {
            let trimmed = part.trim();
            if trimmed.is_empty() {
                None
            } else {
                Some(trimmed.to_string())
            }
        })
        .collect();
    let mut index: u32 = 0;
    for (para_idx, para) in paragraphs.iter().enumerate() {
        let segments = split_with_overlap(para, max_chars_usize, overlap_usize);
        for segment in segments {
            chunks.push(ChunkEntry {
                index,
                paragraph_index: para_idx as u32,
                start: segment.start as u32,
                length: segment.length as u32,
                chars: segment.length as u32,
                reason_code: REASON_SEGMENT,
                score: SCORE_DEFAULT,
            });
            index += 1;
        }
    }
    ChunkPlan {
        max_chars,
        overlap: effective_overlap,
        chunks,
    }
}

pub fn plan_to_json(plan: &ChunkPlan) -> Vec<u8> {
    let mut out = String::new();
    out.push('{');
    out.push_str("\"chunks\":[");
    for (idx, chunk) in plan.chunks.iter().enumerate() {
        if idx > 0 {
            out.push(',');
        }
        out.push('{');
        out.push_str("\"chars\":");
        out.push_str(&chunk.chars.to_string());
        out.push_str(",\"index\":");
        out.push_str(&chunk.index.to_string());
        out.push_str(",\"length\":");
        out.push_str(&chunk.length.to_string());
        out.push_str(",\"paragraph_index\":");
        out.push_str(&chunk.paragraph_index.to_string());
        out.push_str(",\"reason_code\":");
        out.push_str(&chunk.reason_code.to_string());
        out.push_str(",\"score\":");
        out.push_str(&chunk.score.to_string());
        out.push_str(",\"start\":");
        out.push_str(&chunk.start.to_string());
        out.push('}');
    }
    out.push(']');
    out.push_str(",\"max_chars\":");
    out.push_str(&plan.max_chars.to_string());
    out.push_str(",\"overlap\":");
    out.push_str(&plan.overlap.to_string());
    out.push('}');
    out.into_bytes()
}

struct Segment {
    start: usize,
    length: usize,
}

fn split_with_overlap(text: &str, max_chars: usize, overlap: usize) -> Vec<Segment> {
    if max_chars == 0 {
        if text.is_empty() {
            return Vec::new();
        }
        return vec![Segment {
            start: 0,
            length: text.chars().count(),
        }];
    }
    let overlap = effective_overlap(max_chars, overlap);
    let chars: Vec<char> = text.chars().collect();
    let length = chars.len();
    let mut output = Vec::new();
    let mut start = 0usize;
    while start < length {
        let end = std::cmp::min(start + max_chars, length);
        let segment_chars = &chars[start..end];
        let (lead, trail) = trim_bounds(segment_chars);
        if lead < trail {
            output.push(Segment {
                start: start + lead,
                length: trail - lead,
            });
        }
        if end >= length {
            break;
        }
        start = std::cmp::max(end.saturating_sub(overlap), start + 1);
    }
    output
}

fn trim_bounds(chars: &[char]) -> (usize, usize) {
    let mut lead = 0usize;
    let mut trail = chars.len();
    while lead < chars.len() && chars[lead].is_whitespace() {
        lead += 1;
    }
    while trail > lead && chars[trail - 1].is_whitespace() {
        trail -= 1;
    }
    (lead, trail)
}

fn effective_overlap(max_chars: usize, overlap: usize) -> usize {
    if max_chars == 0 {
        return 0;
    }
    if overlap >= max_chars {
        return max_chars / 4;
    }
    overlap
}
