# Retrieval Semantics Specification

## Deterministic Retrieval Plan
Retrieval **must** expose a serializable plan containing:
- query
- scope
- applied filters
- cutoffs
- selected chunk ordering

For identical inputs and index state, the plan **must** be identical.

## Retrieval Trace
Retrieval trace entries **must** include:
- `chunk_id`
- `document_id`
- `page_number`
- `score`
- `rank`
- `reason`

Trace ordering **must** be stable and match ranked retrieval order.

## Trust Grounding
Trust outputs **must** derive from explicit evidence:
- retrieval score distribution
- source diversity
- ingestion diagnostics / fallback flags

Trust **must not** rely on hidden heuristics.

## Citation Semantics
Citations in UI and headless responses **must** be renderings of `retrieval_trace`, not recomputed guesses.
