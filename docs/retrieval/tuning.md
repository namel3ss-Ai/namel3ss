# Retrieval Tuning

Retrieval tuning controls adjust semantic/lexical blending and candidate limits while preserving deterministic ranking and preview output.

## Tunable fields

- `semantic_weight` (0..1)
- `semantic_k` (int)
- `lexical_k` (int)
- `final_top_k` (int)

Runtime state is stored under `state.retrieval.tuning` with canonical key ordering.

## Deterministic preview ordering

Preview rows are sorted by:
1. `final_score` (desc)
2. `semantic_score` (desc)
3. `lexical_score` (desc)
4. `doc_id` (asc)
5. `chunk_id` (asc internal tie-break)

## Tag filtering

`filter_tags` can be provided explicitly or resolved from UI state scopes. Matching is deterministic:

- normalized tags (trimmed, deduped, sorted)
- per-result `matched_tags` sorted ascending
- empty matches return deterministic empty `results` and `retrieval_preview`

## Flows

The platform wires retrieval tuning controls to flow actions when available:

- `set_semantic_weight`
- `set_semantic_k`
- `set_lexical_k`
- `set_final_top_k`

