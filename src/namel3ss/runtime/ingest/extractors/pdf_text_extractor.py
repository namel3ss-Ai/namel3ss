from __future__ import annotations

from namel3ss.ingestion.detect import detect_upload
from namel3ss.ingestion.extract import extract_pages
from namel3ss.runtime.ingest.extractors.extractor_protocol import (
    ExtractedPage,
    ExtractorResult,
    normalize_extractor_metadata,
    normalize_pages,
)


class PdfTextExtractor:
    engine_name = "pdf_text_extractor"
    engine_version = "1"

    def extract(self, content: bytes, *, content_type: str | None = None) -> ExtractorResult:
        detected = detect_upload({"name": "document.pdf", "type": content_type or "application/pdf"}, content=content)
        if str(detected.get("type") or "") != "pdf":
            raise ValueError("pdf text extractor only supports PDF input.")
        pages, method_used = extract_pages(content, detected=detected, mode="primary")
        extracted = [
            ExtractedPage(page_number=index + 1, text=(text if isinstance(text, str) else "").strip())
            for index, text in enumerate(pages)
        ]
        return ExtractorResult(
            engine_name=self.engine_name,
            engine_version=self.engine_version,
            method=method_used,
            pages=normalize_pages(extracted),
            metadata=normalize_extractor_metadata(
                {
                    "content_type": content_type or "application/pdf",
                    "page_count": len(extracted),
                    "parser": "namel3ss.ingestion.extract.extract_pages(mode=primary)",
                }
            ),
        )


__all__ = ["PdfTextExtractor"]
