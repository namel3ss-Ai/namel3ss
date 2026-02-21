from __future__ import annotations

from collections.abc import Callable, Mapping

from namel3ss.runtime.ingest.extractors.extractor_protocol import (
    ExtractedPage,
    ExtractorResult,
    normalize_extractor_metadata,
    normalize_pages,
)
from namel3ss.runtime.ingest.extractors.ocr_backend import build_pdf_ocr_backend, is_ocr_backend_available


OCR_NOT_AVAILABLE_ERROR_CODE = "N3E_OCR_NOT_AVAILABLE"


class OcrNotAvailableError(RuntimeError):
    def __init__(self, message: str = "OCR backend is not available.") -> None:
        super().__init__(message)
        self.error_code = OCR_NOT_AVAILABLE_ERROR_CODE


class PdfOcrExtractor:
    engine_name = "pdf_ocr_extractor"
    engine_version = "1"

    def __init__(
        self,
        *,
        backend: Callable[[bytes], list[str]] | None = None,
        settings: Mapping[str, object] | None = None,
    ) -> None:
        self._backend = backend
        base_settings = {
            "dpi": 300,
            "lang": "eng",
            "page_segmentation_mode": 6,
            "preserve_interword_spaces": 1,
        }
        if isinstance(settings, Mapping):
            for key in sorted(settings.keys(), key=str):
                base_settings[str(key)] = settings[key]
        self._settings = normalize_extractor_metadata(base_settings)

    def is_available(self) -> bool:
        return self._backend is not None

    def extract(self, content: bytes, *, content_type: str | None = None) -> ExtractorResult:
        if self._backend is None:
            raise OcrNotAvailableError()
        pages = self._backend(content)
        extracted = [
            ExtractedPage(page_number=index + 1, text=(text if isinstance(text, str) else "").strip())
            for index, text in enumerate(pages)
        ]
        return ExtractorResult(
            engine_name=self.engine_name,
            engine_version=self.engine_version,
            method="ocr",
            pages=normalize_pages(extracted),
            metadata=normalize_extractor_metadata(
                {
                    "content_type": content_type or "application/pdf",
                    "page_count": len(extracted),
                    "settings": dict(self._settings),
                }
            ),
        )


def create_default_pdf_ocr_extractor(*, settings: Mapping[str, object] | None = None) -> PdfOcrExtractor:
    backend = build_pdf_ocr_backend(settings=settings)
    return PdfOcrExtractor(backend=backend, settings=settings)


def default_pdf_ocr_available() -> bool:
    return is_ocr_backend_available()


__all__ = [
    "OCR_NOT_AVAILABLE_ERROR_CODE",
    "OcrNotAvailableError",
    "PdfOcrExtractor",
    "create_default_pdf_ocr_extractor",
    "default_pdf_ocr_available",
]
