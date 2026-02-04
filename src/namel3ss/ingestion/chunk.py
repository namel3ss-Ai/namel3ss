from __future__ import annotations


def chunk_text(text: str, *, max_chars: int = 800, overlap: int = 100) -> list[dict]:
    if not text:
        return []
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[dict] = []
    chunk_index = 0
    for para in paragraphs:
        for part in _split_with_overlap(para, max_chars=max_chars, overlap=overlap):
            chunk = {
                "chunk_index": chunk_index,
                "text": part,
                "chars": len(part),
            }
            chunks.append(chunk)
            chunk_index += 1
    return chunks


def chunk_pages(pages: list[str], *, max_chars: int = 800, overlap: int = 100) -> list[dict]:
    if not pages:
        return []
    chunks: list[dict] = []
    chunk_index = 0
    for page_number, page in enumerate(pages, start=1):
        page_chunks = chunk_text(page or "", max_chars=max_chars, overlap=overlap)
        for chunk in page_chunks:
            entry = dict(chunk)
            entry["chunk_index"] = chunk_index
            entry["page_number"] = page_number
            chunks.append(entry)
            chunk_index += 1
    return chunks


def chunk_text_with_spans(text: str, *, max_chars: int = 800, overlap: int = 100) -> list[dict]:
    if not text:
        return []
    chunks: list[dict] = []
    for para_text, para_start in _paragraphs_with_offsets(text):
        for part, start, end in _split_with_overlap_spans(para_text, max_chars=max_chars, overlap=overlap):
            chunk = {
                "text": part,
                "chars": len(part),
                "start_char": para_start + start,
                "end_char": para_start + end,
            }
            chunks.append(chunk)
    return chunks


def chunk_pages_with_spans(pages: list[str], *, max_chars: int = 800, overlap: int = 100) -> list[dict]:
    if not pages:
        return []
    chunks: list[dict] = []
    chunk_index = 0
    for page_number, page in enumerate(pages, start=1):
        page_chunks = chunk_text_with_spans(page or "", max_chars=max_chars, overlap=overlap)
        for chunk in page_chunks:
            entry = dict(chunk)
            entry["chunk_index"] = chunk_index
            entry["page_number"] = page_number
            chunks.append(entry)
            chunk_index += 1
    return chunks


def _split_with_overlap(text: str, *, max_chars: int, overlap: int) -> list[str]:
    if max_chars <= 0:
        return [text]
    if overlap >= max_chars:
        overlap = max_chars // 4
    output: list[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + max_chars, length)
        segment = text[start:end].strip()
        if segment:
            output.append(segment)
        if end >= length:
            break
        start = max(end - overlap, start + 1)
    return output


def _split_with_overlap_spans(text: str, *, max_chars: int, overlap: int) -> list[tuple[str, int, int]]:
    if max_chars <= 0:
        return [(text, 0, len(text))]
    if overlap >= max_chars:
        overlap = max_chars // 4
    output: list[tuple[str, int, int]] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + max_chars, length)
        raw_segment = text[start:end]
        segment = raw_segment.strip()
        if segment:
            leading = len(raw_segment) - len(raw_segment.lstrip())
            trailing = len(raw_segment) - len(raw_segment.rstrip())
            output.append((segment, start + leading, end - trailing))
        if end >= length:
            break
        start = max(end - overlap, start + 1)
    return output


def _paragraphs_with_offsets(text: str) -> list[tuple[str, int]]:
    paragraphs: list[tuple[str, int]] = []
    cursor = 0
    for raw in text.split("\n\n"):
        raw_len = len(raw)
        trimmed = raw.strip()
        if trimmed:
            leading = len(raw) - len(raw.lstrip())
            paragraphs.append((trimmed, cursor + leading))
        cursor += raw_len + 2
    return paragraphs


__all__ = ["chunk_pages", "chunk_pages_with_spans", "chunk_text", "chunk_text_with_spans"]
