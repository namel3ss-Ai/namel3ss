# Interim retrieval controls

Studio renders interim retrieval tuning controls inside the `retrieval_explain` element using existing primitives.

## Controls

- Dropdown: semantic candidate count (`set_semantic_k`)
- Dropdown: lexical candidate count (`set_lexical_k`)
- Dropdown: final top-k (`set_final_top_k`)
- Radio group: semantic weight (`set_semantic_weight`)

## Enablement

- Controls are enabled only when matching flow actions exist in the manifest.
- When actions are missing, controls remain visible but disabled with a deterministic reason string.
- Production mode does not expose these controls.

## Action mapping

Each control dispatches an existing `call_flow` action with one numeric input field:

- `k` for candidate and top-k controls
- `weight` for semantic weight

No new UI primitive or action type is introduced in this phase.
