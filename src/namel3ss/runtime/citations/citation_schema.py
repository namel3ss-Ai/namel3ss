from __future__ import annotations

from dataclasses import dataclass


CITATION_INVARIANT_ERROR_CODE = "N3E_CITATION_INVARIANT_BROKEN"
CITATION_SCHEMA_VERSION = "citation_payload@1"


@dataclass(frozen=True)
class CitationPayload:
    snippet: str
    title: str
    source_id: str
    document_id: str
    page_number: int
    chunk_index: int
    chunk_id: str
    score: float

    def to_dict(self) -> dict[str, object]:
        # Keep snippet first to make snippet-first contract explicit.
        return {
            "snippet": self.snippet,
            "title": self.title,
            "source_id": self.source_id,
            "document_id": self.document_id,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "chunk_id": self.chunk_id,
            "score": round(self.score, 4),
        }


__all__ = ["CITATION_INVARIANT_ERROR_CODE", "CITATION_SCHEMA_VERSION", "CitationPayload"]
