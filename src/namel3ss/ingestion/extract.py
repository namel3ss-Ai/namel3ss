from __future__ import annotations

import re
import zlib

from namel3ss.ingestion.extract_pdf_decoding import (
    decode_pdf_hex_string as _decode_pdf_hex_string,
    decode_pdf_string as _decode_pdf_string,
    is_probable_text_stream as _is_probable_text_stream,
    looks_like_readable_text as _looks_like_readable_text,
)
from namel3ss.ingestion.extract_text_utils import (
    extract_docx_text as _extract_docx_text,
    extract_pdf_pages_with_ocr as _extract_pdf_pages_with_ocr,
    extract_pdf_pages_with_pypdf as _extract_pdf_pages_with_pypdf,
    extract_text_bytes as _extract_text_bytes,
    has_non_empty_pages as _has_non_empty_pages,
    has_readable_pages as _has_readable_pages,
    join_pages_text as _join_pages_text,
    normalize_extracted_pages as _normalize_extracted_pages,
    normalize_extracted_text as _normalize_extracted_text,
)
from namel3ss.runtime.ingest.extractors.ocr_backend import extract_image_text_with_ocr


_PDF_STRING_RE = re.compile(rb"\((?:\\.|[^\\)])*\)")
_PDF_HEX_STRING_RE = re.compile(rb"<([0-9A-Fa-f\s]{4,})>")
_PDF_STREAM_RE = re.compile(rb"stream\r?\n", re.IGNORECASE)
_PDF_ENDSTREAM_RE = re.compile(rb"endstream", re.IGNORECASE)
_PDF_FLATE_RE = re.compile(rb"/FlateDecode\b")
_PDF_OBJ_RE = re.compile(rb"(?m)^\s*(\d+)\s+(\d+)\s+obj\b")
_PDF_ENDOBJ_RE = re.compile(rb"(?m)^\s*endobj\b")
_PDF_REF_RE = re.compile(rb"(\d+)\s+(\d+)\s+R")
_PDF_TYPE_RE = re.compile(rb"/Type\s*/([A-Za-z]+)\b")
_PDF_PAGES_RE = re.compile(rb"/Pages\s+(\d+)\s+(\d+)\s+R")
_PDF_KIDS_RE = re.compile(rb"/Kids\s*\[(.*?)\]", re.S)

def extract_text(content: bytes, *, detected: dict, mode: str) -> tuple[str, str]:
    kind = str(detected.get("type") or "text")
    if mode == "layout":
        if kind != "pdf":
            return "", "layout"
        return _extract_pdf_text(content, layout=True), "layout"
    if mode == "ocr":
        if kind == "pdf":
            pages = _extract_pdf_pages_with_ocr(content)
            if _has_non_empty_pages(pages):
                return _join_pages_text(pages), "ocr"
            return _extract_pdf_text(content, layout=True), "ocr"
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


def extract_pages(content: bytes, *, detected: dict, mode: str) -> tuple[list[str], str]:
    kind = str(detected.get("type") or "text")
    if mode == "layout":
        if kind != "pdf":
            return [""], "layout"
        pages = _normalize_extracted_pages(_extract_pdf_pages_with_pypdf(content))
        if _has_readable_pages(pages):
            return pages, "layout"
        pages = _normalize_extracted_pages(_extract_pdf_pages(content, layout=True))
        if pages is None:
            pages = _split_pages(_normalize_extracted_text(_extract_pdf_text(content, layout=True)))
        return pages, "layout"
    if mode == "ocr":
        if kind == "pdf":
            pages = _normalize_extracted_pages(_extract_pdf_pages_with_ocr(content))
            if _has_readable_pages(pages):
                return pages, "ocr"
            pages = _normalize_extracted_pages(_extract_pdf_pages_with_pypdf(content))
            if _has_readable_pages(pages):
                return pages, "ocr"
            pages = _normalize_extracted_pages(_extract_pdf_pages(content, layout=True))
            if pages is None:
                pages = _split_pages(_normalize_extracted_text(_extract_pdf_text(content, layout=True)))
            return pages, "ocr"
        if kind != "image":
            return [""], "ocr"
        return _split_pages(_extract_image_ocr(content)), "ocr"
    if kind == "pdf":
        pages = _normalize_extracted_pages(_extract_pdf_pages_with_pypdf(content))
        if _has_readable_pages(pages):
            return pages, "primary"
        pages = _normalize_extracted_pages(_extract_pdf_pages(content, layout=False))
        if pages is None:
            pages = _split_pages(_normalize_extracted_text(_extract_pdf_text(content, layout=False)))
        return pages, "primary"
    if kind == "docx":
        return _split_pages(_extract_docx_text(content)), "primary"
    if kind == "image":
        return _split_pages(_extract_image_primary(content)), "primary"
    return _split_pages(_extract_text_bytes(content)), "primary"


def extract_pages_fallback(content: bytes, *, detected: dict) -> tuple[list[str], str]:
    kind = str(detected.get("type") or "text")
    if kind == "pdf":
        pages = _normalize_extracted_pages(_extract_pdf_pages_with_pypdf(content))
        if _has_readable_pages(pages):
            return pages, "layout"
        pages = _normalize_extracted_pages(_extract_pdf_pages(content, layout=True))
        if pages is None:
            pages = _split_pages(_normalize_extracted_text(_extract_pdf_text(content, layout=True)))
        return pages, "layout"
    if kind == "image":
        return _split_pages(_extract_image_ocr(content)), "ocr"
    return _split_pages(_extract_text_bytes(content)), "primary"


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


def _extract_pdf_pages(content: bytes, *, layout: bool) -> list[str] | None:
    if not content:
        return None
    objects, order = _parse_pdf_objects(content)
    if not objects:
        return None
    page_ids = _pdf_page_order(objects, order)
    if not page_ids:
        return None
    streams = _pdf_stream_map(objects)
    pages: list[str] = []
    for page_id in page_ids:
        obj = objects.get(page_id)
        if obj is None:
            return None
        contents = _pdf_page_contents(obj)
        stream_payloads: list[bytes] = []
        if contents:
            for ref in contents:
                stream_payloads.extend(streams.get(ref, []))
        else:
            stream_payloads.extend(_extract_streams_from_object(obj))
        pages.append(_pdf_text_from_streams(stream_payloads, layout=layout))
    return pages


def _pdf_text_blocks(content: bytes) -> list[str]:
    blocks: list[str] = []
    for data in _pdf_text_sources(content):
        for raw in _PDF_STRING_RE.findall(data):
            text = _decode_pdf_string(raw[1:-1])
            if _looks_like_readable_text(text):
                blocks.append(text)
        for raw_hex in _PDF_HEX_STRING_RE.findall(data):
            text = _decode_pdf_hex_string(raw_hex)
            if _looks_like_readable_text(text):
                blocks.append(text)
    return blocks


def _pdf_text_sources(content: bytes) -> list[bytes]:
    sources: list[bytes] = []
    for stream, header in _iter_pdf_streams(content):
        if _PDF_FLATE_RE.search(header):
            try:
                payload = zlib.decompress(stream)
            except Exception:
                continue
        else:
            payload = stream
        if _is_probable_text_stream(payload):
            sources.append(payload)
    if not sources:
        sources.append(content)
    return sources


def _pdf_text_from_streams(streams: list[bytes], *, layout: bool) -> str:
    if not streams:
        return ""
    blocks: list[str] = []
    for data in streams:
        for raw in _PDF_STRING_RE.findall(data):
            text = _decode_pdf_string(raw[1:-1])
            if _looks_like_readable_text(text):
                blocks.append(text)
        for raw_hex in _PDF_HEX_STRING_RE.findall(data):
            text = _decode_pdf_hex_string(raw_hex)
            if _looks_like_readable_text(text):
                blocks.append(text)
    joiner = "\n" if layout else " "
    return joiner.join(blocks)


def _parse_pdf_objects(content: bytes) -> tuple[dict[int, bytes], list[int]]:
    objects: dict[int, bytes] = {}
    order: list[int] = []
    for match in _PDF_OBJ_RE.finditer(content):
        obj_id = int(match.group(1))
        start = match.end()
        end = _find_pdf_endobj(content, start)
        if end is None:
            continue
        objects[obj_id] = content[start:end]
        order.append(obj_id)
    return objects, order


def _find_pdf_endobj(content: bytes, start: int) -> int | None:
    pos = start
    while True:
        endobj = _PDF_ENDOBJ_RE.search(content, pos)
        if endobj is None:
            return None
        stream = _PDF_STREAM_RE.search(content, pos, endobj.start())
        if stream is None:
            return endobj.start()
        endstream = _PDF_ENDSTREAM_RE.search(content, stream.end())
        if endstream is None:
            return None
        pos = endstream.end()


def _pdf_page_order(objects: dict[int, bytes], order: list[int]) -> list[int]:
    catalog_id = _pdf_catalog_id(objects, order)
    if catalog_id is not None:
        root = _pdf_pages_root(objects.get(catalog_id))
        if root is not None:
            pages = _collect_pdf_pages(root, objects, set())
            if pages:
                return pages
    return [obj_id for obj_id in order if _pdf_object_type(objects.get(obj_id)) == "Page"]


def _pdf_catalog_id(objects: dict[int, bytes], order: list[int]) -> int | None:
    for obj_id in order:
        if _pdf_object_type(objects.get(obj_id)) == "Catalog":
            return obj_id
    return None


def _pdf_pages_root(obj_bytes: bytes | None) -> int | None:
    if not obj_bytes:
        return None
    stripped = _strip_streams(obj_bytes)
    match = _PDF_PAGES_RE.search(stripped)
    if not match:
        return None
    return int(match.group(1))


def _collect_pdf_pages(obj_id: int, objects: dict[int, bytes], seen: set[int]) -> list[int]:
    if obj_id in seen:
        return []
    seen.add(obj_id)
    obj = objects.get(obj_id)
    obj_type = _pdf_object_type(obj)
    if obj_type == "Page":
        return [obj_id]
    if obj_type != "Pages":
        return []
    kids = _pdf_pages_kids(obj)
    pages: list[int] = []
    for kid in kids:
        pages.extend(_collect_pdf_pages(kid, objects, seen))
    return pages


def _pdf_pages_kids(obj_bytes: bytes | None) -> list[int]:
    if not obj_bytes:
        return []
    stripped = _strip_streams(obj_bytes)
    match = _PDF_KIDS_RE.search(stripped)
    if not match:
        return []
    return [int(item.group(1)) for item in _PDF_REF_RE.finditer(match.group(1))]


def _pdf_page_contents(obj_bytes: bytes) -> list[int]:
    stripped = _strip_streams(obj_bytes)
    idx = stripped.find(b"/Contents")
    if idx == -1:
        return []
    tail = stripped[idx + len(b"/Contents") :].lstrip()
    if not tail:
        return []
    if tail.startswith(b"["):
        end = tail.find(b"]")
        if end == -1:
            return []
        return [int(item.group(1)) for item in _PDF_REF_RE.finditer(tail[1:end])]
    match = _PDF_REF_RE.search(tail)
    if match:
        return [int(match.group(1))]
    return []


def _pdf_object_type(obj_bytes: bytes | None) -> str | None:
    if not obj_bytes:
        return None
    stripped = _strip_streams(obj_bytes)
    match = _PDF_TYPE_RE.search(stripped)
    if not match:
        return None
    try:
        return match.group(1).decode("ascii")
    except Exception:
        return None


def _strip_streams(obj_bytes: bytes) -> bytes:
    output = obj_bytes
    while True:
        start = _PDF_STREAM_RE.search(output)
        if not start:
            return output
        end = _PDF_ENDSTREAM_RE.search(output, start.end())
        if not end:
            return output
        output = output[: start.start()] + output[end.end() :]


def _pdf_stream_map(objects: dict[int, bytes]) -> dict[int, list[bytes]]:
    streams: dict[int, list[bytes]] = {}
    for obj_id, obj_bytes in objects.items():
        payloads = _extract_streams_from_object(obj_bytes)
        if payloads:
            streams[obj_id] = payloads
    return streams


def _extract_streams_from_object(obj_bytes: bytes) -> list[bytes]:
    payloads: list[bytes] = []
    idx = 0
    while True:
        start = _PDF_STREAM_RE.search(obj_bytes, idx)
        if not start:
            break
        end = _PDF_ENDSTREAM_RE.search(obj_bytes, start.end())
        if not end:
            break
        header = obj_bytes[: start.start()]
        payload = obj_bytes[start.end() : end.start()].strip(b"\r\n")
        if _PDF_FLATE_RE.search(header):
            try:
                payload = zlib.decompress(payload)
            except Exception:
                payload = b""
        payloads.append(payload)
        idx = end.end()
    return payloads


def _split_pages(text: str) -> list[str]:
    if "\f" not in text:
        return [text]
    return text.split("\f")


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


def _extract_image_primary(content: bytes) -> str:
    return ""


def _extract_image_ocr(content: bytes) -> str:
    return extract_image_text_with_ocr(content)


__all__ = ["extract_pages", "extract_pages_fallback", "extract_text", "extract_fallback"]
