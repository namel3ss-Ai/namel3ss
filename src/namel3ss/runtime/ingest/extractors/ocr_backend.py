from __future__ import annotations

from collections.abc import Callable, Mapping
from threading import Lock
from typing import Any


_RUNTIME_UNSET = object()
_OCR_RUNTIME: _OcrRuntime | None | object = _RUNTIME_UNSET


class _OcrRuntime:
    def __init__(
        self,
        *,
        cv2_module: object,
        numpy_module: object,
        pdfium_module: object,
        ocr_factory: Callable[[], object],
    ) -> None:
        self._cv2 = cv2_module
        self._np = numpy_module
        self._pdfium = pdfium_module
        self._ocr_factory = ocr_factory
        self._ocr_engine: object | None = None
        self._engine_lock = Lock()
        self._call_lock = Lock()

    def is_available(self) -> bool:
        try:
            self._ensure_engine()
        except Exception:
            return False
        return True

    def extract_pdf_pages(self, content: bytes, *, dpi: int) -> list[str]:
        payload = _coerce_content(content)
        if payload is None:
            return []
        try:
            document = self._pdfium.PdfDocument(payload)
        except Exception:
            return []
        page_count = _coerce_positive_int(len(document), default=0)
        pages: list[str] = []
        try:
            for page_index in range(page_count):
                image = self._render_pdf_page(document, page_index=page_index, dpi=dpi)
                if image is None:
                    pages.append("")
                    continue
                pages.append(_join_text_lines(self._run_ocr(image)))
        finally:
            _safe_close(document)
        return pages

    def extract_image_text(self, content: bytes) -> str:
        payload = _coerce_content(content)
        if payload is None:
            return ""
        try:
            buffer = self._np.frombuffer(payload, dtype=self._np.uint8)
            if int(getattr(buffer, "size", 0)) <= 0:
                return ""
            image = self._cv2.imdecode(buffer, self._cv2.IMREAD_COLOR)
        except Exception:
            return ""
        if image is None:
            return ""
        return _join_text_lines(self._run_ocr(image))

    def _run_ocr(self, image: Any) -> list[str]:
        try:
            engine = self._ensure_engine()
            with self._call_lock:
                result, _elapsed = engine(image)  # type: ignore[misc]
        except Exception:
            return []
        return _extract_text_lines(result)

    def _ensure_engine(self) -> object:
        with self._engine_lock:
            if self._ocr_engine is None:
                self._ocr_engine = self._ocr_factory()
        return self._ocr_engine

    def _render_pdf_page(self, document: object, *, page_index: int, dpi: int) -> Any | None:
        page = None
        bitmap = None
        try:
            page = document[page_index]  # type: ignore[index]
            scale = max(0.25, float(dpi) / 72.0)
            bitmap = page.render(scale=scale)
            image = bitmap.to_numpy()
            if hasattr(image, "copy"):
                return image.copy()
            return image
        except Exception:
            return None
        finally:
            _safe_close(bitmap)
            _safe_close(page)


def build_pdf_ocr_backend(*, settings: Mapping[str, object] | None = None) -> Callable[[bytes], list[str]] | None:
    runtime = _resolve_runtime()
    if runtime is None:
        return None
    dpi = _coerce_positive_int((settings or {}).get("dpi"), default=300)

    def _backend(content: bytes) -> list[str]:
        return runtime.extract_pdf_pages(content, dpi=dpi)

    return _backend


def extract_image_text_with_ocr(content: bytes) -> str:
    runtime = _resolve_runtime()
    if runtime is None:
        return ""
    return runtime.extract_image_text(content)


def is_ocr_backend_available() -> bool:
    runtime = _resolve_runtime()
    return runtime.is_available() if runtime is not None else False


def _resolve_runtime() -> _OcrRuntime | None:
    global _OCR_RUNTIME
    if _OCR_RUNTIME is not _RUNTIME_UNSET:
        return _OCR_RUNTIME if isinstance(_OCR_RUNTIME, _OcrRuntime) else None
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
        import pypdfium2 as pdfium  # type: ignore
        from rapidocr_onnxruntime import RapidOCR  # type: ignore
    except Exception:
        _OCR_RUNTIME = None
        return None
    _OCR_RUNTIME = _OcrRuntime(
        cv2_module=cv2,
        numpy_module=np,
        pdfium_module=pdfium,
        ocr_factory=RapidOCR,
    )
    return _OCR_RUNTIME


def _extract_text_lines(payload: Any) -> list[str]:
    if not isinstance(payload, list):
        return []
    lines: list[str] = []
    for item in payload:
        text = _line_text(item)
        if text:
            lines.append(text)
    return lines


def _line_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        field = value.get("text")
        if isinstance(field, str):
            return field.strip()
        return ""
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        field = value[1]
        if isinstance(field, str):
            return field.strip()
    return ""


def _join_text_lines(lines: list[str]) -> str:
    if not lines:
        return ""
    return "\n".join(line for line in lines if line)


def _coerce_content(content: bytes) -> bytes | None:
    if isinstance(content, bytes):
        return content
    if isinstance(content, bytearray):
        return bytes(content)
    if isinstance(content, memoryview):
        return content.tobytes()
    return None


def _coerce_positive_int(value: object, *, default: int) -> int:
    try:
        resolved = int(value)
    except Exception:
        return default
    if resolved <= 0:
        return default
    return resolved


def _safe_close(value: object | None) -> None:
    if value is None:
        return
    close = getattr(value, "close", None)
    if callable(close):
        try:
            close()
        except Exception:
            return


__all__ = ["build_pdf_ocr_backend", "extract_image_text_with_ocr", "is_ocr_backend_available"]
