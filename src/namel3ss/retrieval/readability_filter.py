from __future__ import annotations

from namel3ss.ingestion.gate import gate_quality
from namel3ss.ingestion.signals import compute_signals


def should_skip_unreadable_chunk(
    *,
    text: str,
    explain_builder,
    chunk_id: str,
    ingestion_phase: str,
    page_number: int,
    chunk_index: int,
    order_index: int,
    quality: str,
    vector_score: float | None,
) -> bool:
    _, reasons = gate_quality(compute_signals(text, detected={}))
    if "unreadable_text_pattern" not in reasons:
        return False
    if explain_builder is not None:
        explain_builder.add_filtered(
            chunk_id=chunk_id,
            ingestion_phase=ingestion_phase,
            keyword_overlap=0,
            page_number=page_number,
            chunk_index=chunk_index,
            order_index=order_index,
            quality=quality,
            vector_score=vector_score,
        )
    return True


__all__ = ["should_skip_unreadable_chunk"]
