from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from namel3ss.runtime.ingest.chunking.chunk_id import (
    canonical_chunk_text,
    stable_chunk_id,
    stable_source_id,
)
from namel3ss.runtime.ingest.extractors.extractor_protocol import ExtractedPage, ExtractorResult
from namel3ss.runtime.ingest.extractors.pdf_ocr_extractor import OcrNotAvailableError, PdfOcrExtractor
from namel3ss.runtime.ingest.extractors.pdf_text_extractor import PdfTextExtractor


@dataclass(frozen=True)
class IngestChunk:
    chunk_id: str
    source_id: str
    document_id: str
    page_number: int
    chunk_index: int
    text: str
    metadata: dict[str, object]
    bboxes: tuple[dict[str, object], ...] = ()

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "chunk_id": self.chunk_id,
            "chunk_index": self.chunk_index,
            "document_id": self.document_id,
            "metadata": dict(self.metadata),
            "page_number": self.page_number,
            "source_id": self.source_id,
            "text": self.text,
        }
        if self.bboxes:
            payload["bboxes"] = [dict(item) for item in self.bboxes]
        return payload


@dataclass(frozen=True)
class IngestPipelineResult:
    document_id: str
    method_used: str
    ocr_used: bool
    extraction_engines: tuple[dict[str, object], ...]
    chunks: tuple[IngestChunk, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "chunks": [chunk.to_dict() for chunk in self.chunks],
            "document_id": self.document_id,
            "extraction_engines": [dict(item) for item in self.extraction_engines],
            "method_used": self.method_used,
            "ocr_used": self.ocr_used,
        }


def run_ingest_pipeline(
    *,
    doc_id: str,
    content: bytes,
    content_type: str | None = "application/pdf",
    text_extractor: PdfTextExtractor | None = None,
    ocr_extractor: PdfOcrExtractor | None = None,
    enable_ocr: bool = True,
    require_ocr: bool = False,
    chunk_size: int = 900,
    chunk_overlap: int = 150,
) -> IngestPipelineResult:
    resolved_doc_id = doc_id.strip()
    if not resolved_doc_id:
        raise ValueError("doc_id is required.")
    primary_extractor = text_extractor or PdfTextExtractor()
    primary_result = primary_extractor.extract(content, content_type=content_type)
    extraction_engines: list[dict[str, object]] = [_engine_metadata(primary_result, status="ok")]

    selected_result = primary_result
    ocr_used = False
    if enable_ocr and not _has_text(primary_result.pages):
        if ocr_extractor is None:
            if require_ocr:
                raise OcrNotAvailableError()
        else:
            try:
                ocr_result = ocr_extractor.extract(content, content_type=content_type)
                extraction_engines.append(_engine_metadata(ocr_result, status="ok"))
                if _has_text(ocr_result.pages):
                    selected_result = ocr_result
                    ocr_used = True
            except OcrNotAvailableError:
                extraction_engines.append(
                    {
                        "engine_name": ocr_extractor.engine_name,
                        "engine_version": ocr_extractor.engine_version,
                        "error_code": "N3E_OCR_NOT_AVAILABLE",
                        "status": "unavailable",
                    }
                )
                if require_ocr:
                    raise

    chunks = _build_chunks(
        doc_id=resolved_doc_id,
        pages=selected_result.pages,
        chunk_size=max(1, int(chunk_size)),
        chunk_overlap=max(0, int(chunk_overlap)),
        extractor=selected_result,
    )
    return IngestPipelineResult(
        document_id=resolved_doc_id,
        method_used=selected_result.method,
        ocr_used=ocr_used,
        extraction_engines=tuple(extraction_engines),
        chunks=tuple(chunks),
    )


def _has_text(pages: tuple[ExtractedPage, ...]) -> bool:
    return any(canonical_chunk_text(page.text) for page in pages)


def _build_chunks(
    *,
    doc_id: str,
    pages: tuple[ExtractedPage, ...],
    chunk_size: int,
    chunk_overlap: int,
    extractor: ExtractorResult,
) -> list[IngestChunk]:
    chunks: list[IngestChunk] = []
    for page in sorted(pages, key=lambda item: item.page_number):
        pieces = _split_page_text(page.text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        for chunk_index, piece in enumerate(pieces):
            text = canonical_chunk_text(piece)
            if not text:
                continue
            chunk_id = stable_chunk_id(
                doc_id=doc_id,
                page_number=page.page_number,
                chunk_index=chunk_index,
                text=text,
            )
            source_id = stable_source_id(doc_id=doc_id, page_number=page.page_number, chunk_index=chunk_index)
            metadata = {
                "engine_name": extractor.engine_name,
                "engine_version": extractor.engine_version,
                "method": extractor.method,
            }
            bboxes = _normalize_bboxes(page.bboxes)
            chunks.append(
                IngestChunk(
                    chunk_id=chunk_id,
                    source_id=source_id,
                    document_id=doc_id,
                    page_number=page.page_number,
                    chunk_index=chunk_index,
                    text=text,
                    metadata=metadata,
                    bboxes=bboxes,
                )
            )
    return chunks


def _split_page_text(text: str, *, chunk_size: int, chunk_overlap: int) -> list[str]:
    normalized = canonical_chunk_text(text)
    if not normalized:
        return []
    if len(normalized) <= chunk_size:
        return [normalized]
    step = max(1, chunk_size - min(chunk_overlap, chunk_size - 1))
    rows: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + chunk_size)
        rows.append(normalized[start:end])
        if end >= len(normalized):
            break
        start += step
    return rows


def _normalize_bboxes(value: tuple[dict[str, object], ...]) -> tuple[dict[str, object], ...]:
    normalized: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        normalized.append({str(key): item[key] for key in sorted(item.keys(), key=str)})
    normalized.sort(key=lambda item: (str(item.get("page") or ""), str(item.get("x0") or ""), str(item.get("y0") or "")))
    return tuple(normalized)


def _engine_metadata(result: ExtractorResult, *, status: str) -> dict[str, object]:
    return {
        "engine_name": result.engine_name,
        "engine_version": result.engine_version,
        "metadata": dict(result.metadata),
        "method": result.method,
        "status": status,
    }


__all__ = ["IngestChunk", "IngestPipelineResult", "run_ingest_pipeline"]
