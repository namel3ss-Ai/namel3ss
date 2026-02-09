# Deterministic Retrieval Evidence

Namel3ss retrieval now emits explicit deterministic evidence objects for headless and Studio clients:

- `retrieval_plan`
- `retrieval_trace`
- `trust_score_details`

## Retrieval plan

`retrieval_plan` captures deterministic retrieval inputs and cutoffs:

- query
- active scope
- quality/tier filters
- selected chunk ids
- ordering and candidate/selected counts

## Retrieval trace

`retrieval_trace` is the citation source of truth. Each row includes:

- `chunk_id`
- `document_id`
- `page_number`
- `score` (bounded to `[0, 1]`)
- `rank` (1-based deterministic order)
- `reason` (for example `keyword_match`, `semantic_match`, `fallback_inclusion`)

## Trust score details

`trust_score_details` is computed from retrieval evidence with a documented deterministic formula:

- average retrieval score
- source diversity
- retrieval coverage
- explicit penalties for warn quality and OCR fallback

No timestamps or random IDs are used. Equal input state and query produce equal retrieval artifacts.
