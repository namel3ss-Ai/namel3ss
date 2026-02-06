from __future__ import annotations

import io
import re
import wave


_PDF_PAGE_RE = re.compile(rb"/Type\s*/Page\b")
_PDF_IMAGE_RE = re.compile(rb"/Subtype\s*/Image\b")


def detect_upload(metadata: dict, *, content: bytes | None = None) -> dict:
    content_type = str(metadata.get("content_type") or "").lower()
    name = str(metadata.get("name") or "")
    ext = _extension(name)
    kind = _detect_type(content_type, ext)
    page_count = None
    has_images = None
    image_resolution = None
    audio_duration_ms = None
    if kind == "pdf" and content is not None:
        page_count = _pdf_page_count(content)
        has_images = _pdf_has_images(content)
    if kind == "image" and content is not None:
        image_resolution = _image_resolution(content)
    if kind == "audio" and content is not None:
        audio_duration_ms = _audio_duration_ms(content)
    return {
        "type": kind,
        "page_count": page_count,
        "has_images": has_images,
        "image_resolution": image_resolution,
        "audio_duration_ms": audio_duration_ms,
    }


def _detect_type(content_type: str, ext: str) -> str:
    if content_type.startswith("text/") or ext in {".txt", ".md", ".csv"}:
        return "text"
    if content_type == "application/pdf" or ext == ".pdf":
        return "pdf"
    if content_type in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    } or ext == ".docx":
        return "docx"
    if content_type.startswith("audio/") or ext in {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac"}:
        return "audio"
    if content_type.startswith("image/") or ext in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff"}:
        return "image"
    return "text"


def _extension(name: str) -> str:
    if not name:
        return ""
    dot = name.rfind(".")
    if dot == -1:
        return ""
    return name[dot:].lower()


def _pdf_page_count(content: bytes) -> int:
    matches = list(_PDF_PAGE_RE.finditer(content))
    return len(matches)


def _pdf_has_images(content: bytes) -> bool:
    return _PDF_IMAGE_RE.search(content) is not None


def _image_resolution(content: bytes) -> dict[str, int] | None:
    if content.startswith(b"\x89PNG\r\n\x1a\n") and len(content) >= 24:
        return {
            "width": int.from_bytes(content[16:20], "big"),
            "height": int.from_bytes(content[20:24], "big"),
        }
    if content.startswith(b"GIF8") and len(content) >= 10:
        return {
            "width": int.from_bytes(content[6:8], "little"),
            "height": int.from_bytes(content[8:10], "little"),
        }
    if content.startswith(b"BM") and len(content) >= 26:
        width = int.from_bytes(content[18:22], "little", signed=True)
        height = int.from_bytes(content[22:26], "little", signed=True)
        if width > 0 and height != 0:
            return {"width": width, "height": abs(height)}
    return None


def _audio_duration_ms(content: bytes) -> int | None:
    if not (content.startswith(b"RIFF") and b"WAVE" in content[:16]):
        return None
    try:
        with wave.open(io.BytesIO(content), "rb") as wav_reader:
            frames = wav_reader.getnframes()
            rate = wav_reader.getframerate()
            if rate <= 0:
                return None
            duration_ms = int((frames / rate) * 1000)
            return duration_ms if duration_ms >= 0 else None
    except Exception:
        return None


__all__ = ["detect_upload"]
