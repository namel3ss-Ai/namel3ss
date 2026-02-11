# Slider

The `slider` control is a deterministic numeric range input for retrieval tuning and other bounded numeric state updates.

## Capability

`ui.slider` is required.

If missing, compile fails with:

`Capability missing: ui.slider is required to use 'slider' controls. Add 'capability is ui.slider' to the manifest.`

## Syntax

```ai
spec is "1.0"

capabilities:
  ui.slider
  ui.tooltip

flow "set_semantic_weight":
  return "ok"

page "Tuning":
  slider "Semantic weight":
    min is 0
    max is 1
    step is 0.05
    value is state.retrieval.semantic_weight
    on change run "set_semantic_weight"
    help is "Blend semantic and lexical retrieval."
```

Required fields:
- `min`
- `max`
- `step`
- `value`
- `on change run`

## Validation

- `min < max`
- `step > 0`
- `value` must reference `state.<path>`
- duplicate slider labels in the same container are compile-time errors

## Determinism

- Slider IDs are stable manifest IDs derived from page/path position.
- `on_change` dispatch uses stable action IDs.
- Same input state always yields the same slider manifest payload.
