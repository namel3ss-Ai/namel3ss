from __future__ import annotations

import html
import re
import zipfile
from io import BytesIO
import zlib


_PDF_STRING_RE = re.compile(rb"\((?:\\.|[^\\)])*\)")
_PDF_STREAM_RE = re.compile(rb"stream\r?\n", re.IGNORECASE)
_PDF_ENDSTREAM_RE = re.compile(rb"endstream", re.IGNORECASE)
_PDF_FLATE_RE = re.compile(rb"/FlateDecode\b")


def extract_text(content: bytes, *, detected: dict, mode: str) -> tuple[str, str]:
    kind = str(detected.get("type") or "text")
    if mode == "layout":
        if kind != "pdf":
            return "", "layout"
        return _extract_pdf_text(content, layout=True), "layout"
    if mode == "ocr":
        if kind != "image":
            return "", "ocr"
        return _extract_image_ocr(content), "ocr"
    if kind == "pdf":
        return _extract_pdf_text(content, layout=False), "primary"
    if kind == "docx":
        return _extract_docx_text(content), "primary"
    if kind == "image":
        return _extract_image_primary(content), "primary"
    return _extract_text_bytes(content), "primary"


def extract_fallback(content: bytes, *, detected: dict) -> tuple[str, str]:
    kind = str(detected.get("type") or "text")
    if kind == "pdf":
        return _extract_pdf_text(content, layout=True), "layout"
    if kind == "image":
        return _extract_image_ocr(content), "ocr"
    return _extract_text_bytes(content), "primary"


def _extract_text_bytes(content: bytes) -> str:
    if not content:
        return ""
    text = content.decode("utf-8", errors="replace")
    if _replacement_ratio(text) > 0.05:
        return content.decode("latin-1", errors="replace")
    return text


def _replacement_ratio(text: str) -> float:
    if not text:
        return 0.0
    replaced = text.count("\ufffd")
    return replaced / max(len(text), 1)


def _extract_docx_text(content: bytes) -> str:
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


def _extract_pdf_text(content: bytes, *, layout: bool) -> str:
    if not content:
        return ""
    strings = []
    for block in _pdf_text_blocks(content):
        if not block:
            continue
        strings.append(block)
    joiner = "\n" if layout else " "
    return joiner.join(strings)


def _pdf_text_blocks(content: bytes) -> list[str]:
    blocks: list[str] = []
    for data in _pdf_text_sources(content):
        for raw in _PDF_STRING_RE.findall(data):
            text = _decode_pdf_string(raw[1:-1])
            if text:
                blocks.append(text)
    return blocks


def _pdf_text_sources(content: bytes) -> list[bytes]:
    sources = [content]
    for stream, header in _iter_pdf_streams(content):
        if _PDF_FLATE_RE.search(header):
            try:
                sources.append(zlib.decompress(stream))
            except Exception:
                continue
    return sources


def _iter_pdf_streams(content: bytes) -> list[tuple[bytes, bytes]]:
    streams: list[tuple[bytes, bytes]] = []
    idx = 0
    while True:
        start = _PDF_STREAM_RE.search(content, idx)
        if not start:
            break
        stream_start = start.end()
        end = _PDF_ENDSTREAM_RE.search(content, stream_start)
        if not end:
            break
        stream_data = content[stream_start : end.start()]
        header_start = max(0, start.start() - 200)
        header = content[header_start : start.start()]
        streams.append((stream_data.strip(b"\r\n"), header))
        idx = end.end()
    return streams


def _decode_pdf_string(raw: bytes) -> str:
    output = []
    idx = 0
    while idx < len(raw):
        char = raw[idx]
        if char == 92:  # backslash
            idx += 1
            if idx >= len(raw):
                break
            esc = raw[idx]
            if esc in b"nrtbf":
                output.append({"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f"}[chr(esc)])
            elif esc in b"\\()":
                output.append(chr(esc))
            elif 48 <= esc <= 55:
                octal = bytes([esc])
                for _ in range(2):
                    if idx + 1 < len(raw) and 48 <= raw[idx + 1] <= 55:
                        idx += 1
                        octal += bytes([raw[idx]])
                    else:
                        break
                try:
                    output.append(chr(int(octal, 8)))
                except Exception:
                    pass
            else:
                output.append(chr(esc))
        else:
            output.append(chr(char))
        idx += 1
    return "".join(output)


def _extract_image_primary(content: bytes) -> str:
    return ""


def _extract_image_ocr(content: bytes) -> str:
    return ""


__all__ = ["extract_text", "extract_fallback"]
