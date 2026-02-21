# RAG overview

This page defines retrieval-augmented generation (RAG) in namel3ss as a deterministic, end-to-end workflow. It is the single authoritative overview for building RAG apps.

## What "RAG in namel3ss" means
- Uploads are ingested into deterministic text chunks with stable provenance.
- Retrieval returns ordered chunks based on explicit, deterministic rules.
- Answering uses retrieved chunks and must include citations.
- UI surfaces can show citations, PDF previews, and exact source highlights.
- Explain mode produces a replayable record of selection and citations.
- Optional embeddings improve recall without changing `.ai` files.

RAG is a runtime capability. Prompts are runtime-owned. `.ai` files never contain prompt logic or vector math.

## End-to-end pipeline
upload -> ingest -> retrieve -> answer -> cite -> preview -> highlight -> explain

## What you build vs what the runtime owns

You build:
- Flows that call ingestion, retrieval, and answer actions.
- Records and state fields that store results, citations, and previews.
- UI that renders answers, citation lists, and page previews.

The runtime owns:
- Text extraction and chunking.
- Deterministic ordering and selection.
- Citation validation and mapping.
- Preview metadata and highlight anchors.
- Explain bundles with stable ordering.
- Optional embeddings (configured at runtime only).

## Determinism guarantees
- Same inputs produce the same chunks, ordering, answers, and citations.
- Ordering is stable and documented (no randomness, no timestamps).
- Explain output is replayable and matches the runtime decisions.
- Citations map to stable chunk ids and page numbers.

## Optional embeddings (runtime-only)
Embeddings are enabled via runtime configuration, not in `.ai` files.
When enabled, embeddings expand candidate coverage before the final deterministic ordering.
When disabled, retrieval is identical to keyword-based retrieval.

## How developers interact with RAG
- Ingestion writes reports under `state.ingestion` and chunks under `state.index.chunks`.
- Retrieval returns ordered chunks with `chunk_id`, `page_number`, and `source_name`.
- Answer flows store the answer text and citations in state for UI rendering.
- UI can render `citations` and preview by using the returned chunk and page metadata.

See:
- [Ingestion](docs/runtime/ingestion.md)
- [Retrieval](docs/runtime/retrieval.md)
- [Advanced custom answer flow](docs/rag/advanced_custom_answer_flow.md)

## Common failure cases
- Uncited answers are rejected deterministically.
- Missing pages or previews result in a clear, deterministic "unavailable" state.
- Highlight anchors are absent when the source format cannot support them.
- Embedding configuration errors fail deterministically during ingestion or retrieval.
