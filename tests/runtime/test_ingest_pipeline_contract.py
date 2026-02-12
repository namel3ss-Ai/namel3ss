from __future__ import annotations

from dataclasses import dataclass

import pytest

from namel3ss.runtime.ingest.extractors.extractor_protocol import ExtractedPage, ExtractorResult
from namel3ss.runtime.ingest.extractors.pdf_ocr_extractor import OcrNotAvailableError, PdfOcrExtractor
from namel3ss.runtime.ingest.pipeline.ingest_pipeline import run_ingest_pipeline


SCANNED_PDF_FIXTURE = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"


@dataclass
class StubTextExtractor:
    pages: tuple[ExtractedPage, ...]
    engine_name: str = "stub_text"
    engine_version: str = "1"

    def extract(self, content: bytes, *, content_type: str | None = None) -> ExtractorResult:
        return ExtractorResult(
            engine_name=self.engine_name,
            engine_version=self.engine_version,
            method="text",
            pages=self.pages,
            metadata={"content_type": content_type or "application/pdf"},
        )


def test_ingest_pipeline_is_repeat_run_deterministic() -> None:
    text_extractor = StubTextExtractor(
        pages=(
            ExtractedPage(page_number=1, text="Alpha beta gamma delta epsilon."),
            ExtractedPage(page_number=2, text="Zeta eta theta iota kappa."),
        )
    )
    first = run_ingest_pipeline(
        doc_id="doc-1",
        content=SCANNED_PDF_FIXTURE,
        text_extractor=text_extractor,
        enable_ocr=False,
        chunk_size=16,
        chunk_overlap=4,
    )
    second = run_ingest_pipeline(
        doc_id="doc-1",
        content=SCANNED_PDF_FIXTURE,
        text_extractor=text_extractor,
        enable_ocr=False,
        chunk_size=16,
        chunk_overlap=4,
    )
    assert first.to_dict() == second.to_dict()


def test_ingest_pipeline_uses_ocr_when_text_is_empty() -> None:
    text_extractor = StubTextExtractor(pages=(ExtractedPage(page_number=1, text=""),))
    ocr_extractor = PdfOcrExtractor(backend=lambda _content: ["Scanned OCR text from page 1."])
    result = run_ingest_pipeline(
        doc_id="doc-scan",
        content=SCANNED_PDF_FIXTURE,
        text_extractor=text_extractor,
        ocr_extractor=ocr_extractor,
        enable_ocr=True,
    )
    assert result.method_used == "ocr"
    assert result.ocr_used is True
    assert result.chunks
    assert result.chunks[0].source_id == "doc-scan:1:0"


def test_ingest_pipeline_raises_when_ocr_required_but_unavailable() -> None:
    text_extractor = StubTextExtractor(pages=(ExtractedPage(page_number=1, text=""),))
    with pytest.raises(OcrNotAvailableError) as excinfo:
        run_ingest_pipeline(
            doc_id="doc-scan",
            content=SCANNED_PDF_FIXTURE,
            text_extractor=text_extractor,
            ocr_extractor=None,
            enable_ocr=True,
            require_ocr=True,
        )
    assert excinfo.value.error_code == "N3E_OCR_NOT_AVAILABLE"
