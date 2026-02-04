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


__all__ = ["chunk_pages", "chunk_text"]
