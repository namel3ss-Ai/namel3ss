# Diagnostics Panel

The diagnostics panel supports deterministic filtering and sorting for retrieval-focused debugging.

## Sort options

- `severity`
- `semantic score`
- `lexical score`
- `final score`
- `doc id`

Score sorts use stable tie-breaking and deterministic ordering.

## Filters

Toggles:

- `semantic`
- `lexical`
- `final`

Rows are shown only when at least one enabled toggle matches the row mode set.

## Per-row metadata

Each rendered row includes stable metadata:

- `doc_id`
- `semantic_score`
- `lexical_score`
- `final_score`

## Determinism

- repeated renders over the same diagnostics payload produce the same row order
- score sorting has fixed numeric comparison and tie-break rules
- empty filter state shows a stable empty-state row

