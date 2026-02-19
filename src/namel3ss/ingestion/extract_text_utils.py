from __future__ import annotations

import html
import re
import zipfile
from io import BytesIO

from namel3ss.runtime.ingest.extractors.pdf_ocr_extractor import create_default_pdf_ocr_extractor

_DEFAULT_PDF_OCR_EXTRACTOR = None


def extract_text_bytes(content: bytes) -> str:
    if not content:
        return ""
    text = content.decode("utf-8", errors="replace")
    if _replacement_ratio(text) > 0.05:
        return content.decode("latin-1", errors="replace")
    return text


def extract_docx_text(content: bytes) -> str:
    if not content:
        return ""
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            data = archive.read("word/document.xml")
    except Exception:
        return ""
    try:
        xml_text = data.decode("utf-8", errors="replace")
    except Exception:
        xml_text = data.decode("latin-1", errors="replace")
    paragraphs = []
    for para in re.findall(r"<w:p[\\s\\S]*?</w:p>", xml_text):
        runs = re.findall(r"<w:t[^>]*>(.*?)</w:t>", para)
        if not runs:
            continue
        text = "".join(html.unescape(run) for run in runs)
        if text.strip():
            paragraphs.append(text.strip())
    return "\n\n".join(paragraphs)


def extract_pdf_pages_with_pypdf(content: bytes) -> list[str] | None:
    if not content:
        return None
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return None
    try:
        reader = PdfReader(BytesIO(content))
    except Exception:
        return None
    pages: list[str] = []
    for page in list(getattr(reader, "pages", []) or []):
        text = ""
        try:
            extracted = page.extract_text()
            if isinstance(extracted, str):
                text = extracted
        except Exception:
            text = ""
        pages.append(normalize_extracted_text(text).strip())
    return pages


def extract_pdf_pages_with_ocr(content: bytes) -> list[str] | None:
    extractor = _get_pdf_ocr_extractor()
    if extractor is None or not extractor.is_available():
        return None
    try:
        result = extractor.extract(content, content_type="application/pdf")
    except Exception:
        return None
    pages: list[str] = []
    for page in result.pages:
        text = page.text if isinstance(page.text, str) else ""
        pages.append(normalize_extracted_text(text).strip())
    return pages


def join_pages_text(pages: list[str] | None) -> str:
    if not pages:
        return ""
    return "\f".join(page for page in pages if isinstance(page, str))


def has_non_empty_pages(pages: list[str] | None) -> bool:
    if pages is None:
        return False
    for page in pages:
        if isinstance(page, str) and page.strip():
            return True
    return False


def normalize_extracted_pages(pages: list[str] | None) -> list[str] | None:
    if pages is None:
        return None
    normalized: list[str] = []
    for page in pages:
        if isinstance(page, str):
            normalized.append(normalize_extracted_text(page).strip())
        else:
            normalized.append("")
    return normalized


def normalize_extracted_text(text: str) -> str:
    if not text:
        return ""
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    return _repair_utf8_mojibake(cleaned)


def has_readable_pages(pages: list[str] | None) -> bool:
    if not has_non_empty_pages(pages):
        return False
    if pages is None:
        return False
    for page in pages:
        if _is_readable_page(page):
            return True
    return False


def _replacement_ratio(text: str) -> float:
    if not text:
        return 0.0
    replaced = text.count("\ufffd")
    return replaced / max(len(text), 1)


def _repair_utf8_mojibake(text: str) -> str:
    if not text:
        return text
    best = text
    best_score = _readability_score(text)
    for source_encoding in ("latin-1", "cp1252"):
        try:
            candidate = text.encode(source_encoding, errors="strict").decode("utf-8", errors="strict")
        except Exception:
            continue
        candidate_score = _readability_score(candidate)
        if candidate_score > best_score + 1.0:
            best = candidate
            best_score = candidate_score
    return best


def _is_readable_page(text: str | None) -> bool:
    if not isinstance(text, str):
        return False
    trimmed = text.strip()
    if len(trimmed) < 2:
        return False
    letter_count = sum(1 for ch in trimmed if ch.isalpha())
    if letter_count == 0:
        return False
    mojibake_pairs = _mojibake_pair_count(trimmed)
    if mojibake_pairs >= 3 and mojibake_pairs * 5 >= letter_count:
        return False
    return _readability_score(trimmed) > 0


def _mojibake_pair_count(text: str) -> int:
    count = 0
    if len(text) < 2:
        return count
    for idx in range(len(text) - 1):
        ch = text[idx]
        nxt = text[idx + 1]
        if ch in {"Ã", "Â", "â"} and 0x80 <= ord(nxt) <= 0xBF:
            count += 1
    return count


def _readability_score(text: str) -> float:
    if not text:
        return -1000.0
    letters = sum(1 for ch in text if ch.isalpha())
    digits = sum(1 for ch in text if ch.isdigit())
    spaces = sum(1 for ch in text if ch.isspace())
    controls = sum(1 for ch in text if ord(ch) < 32 and ch not in "\n\r\t")
    replacement = text.count("\ufffd")
    mojibake_leads = sum(1 for ch in text if ch in {"Ã", "Â", "â"})
    mojibake_pairs = _mojibake_pair_count(text)
    return (
        float(letters)
        + float(digits) * 0.35
        + float(spaces) * 0.1
        - float(controls) * 3.0
        - float(replacement) * 6.0
        - float(mojibake_leads) * 1.25
        - float(mojibake_pairs) * 4.0
    )


def _get_pdf_ocr_extractor():
    global _DEFAULT_PDF_OCR_EXTRACTOR
    if _DEFAULT_PDF_OCR_EXTRACTOR is None:
        _DEFAULT_PDF_OCR_EXTRACTOR = create_default_pdf_ocr_extractor()
    return _DEFAULT_PDF_OCR_EXTRACTOR


__all__ = [
    "extract_docx_text",
    "extract_pdf_pages_with_ocr",
    "extract_pdf_pages_with_pypdf",
    "extract_text_bytes",
    "has_non_empty_pages",
    "has_readable_pages",
    "join_pages_text",
    "normalize_extracted_pages",
    "normalize_extracted_text",
]
