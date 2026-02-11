# Citations

Enhanced citations provide stable inline chips plus deterministic snippet previews and drawer linking.

## Capability

`ui.citations_enhanced` enables enhanced chip/snippet behavior.

If missing, the compiler emits:

`Warning: Enhanced citations are disabled (missing capability ui.citations_enhanced). Falling back to legacy citations UI.`

Fallback behavior is explicit and deterministic.

## Citation contract

Each citation entry includes:

- `citation_id` (stable; generated when missing)
- `index` (1-based, stable order)
- `title`
- `source_id` or `url`
- optional deterministic `snippet` truncation

## Sources drawer mapping

- chips and drawer rows use `data-citation-id`
- answer click focuses the matching drawer entry
- drawer selection can resolve back to the matching citation ID

## Snippet truncation

- whitespace normalized
- deterministic max length
- truncated values end with `...`

