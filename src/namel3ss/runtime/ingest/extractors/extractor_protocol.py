from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    text: str
    bboxes: tuple[dict[str, object], ...] = ()


@dataclass(frozen=True)
class ExtractorResult:
    engine_name: str
    engine_version: str
    method: str
    pages: tuple[ExtractedPage, ...]
    metadata: dict[str, object]


class DocumentExtractor(Protocol):
    engine_name: str
    engine_version: str

    def extract(self, content: bytes, *, content_type: str | None = None) -> ExtractorResult:
        ...


def normalize_extractor_metadata(metadata: Mapping[str, object] | None) -> dict[str, object]:
    if not isinstance(metadata, Mapping):
        return {}
    return {str(key): metadata[key] for key in sorted(metadata.keys(), key=str)}


def normalize_pages(pages: Sequence[ExtractedPage]) -> tuple[ExtractedPage, ...]:
    ordered = sorted(
        pages,
        key=lambda item: (int(item.page_number), item.text),
    )
    return tuple(ordered)


__all__ = [
    "DocumentExtractor",
    "ExtractedPage",
    "ExtractorResult",
    "normalize_extractor_metadata",
    "normalize_pages",
]
