# Tooltip

`tooltip` renders deterministic collapsible help text anchored to a control label.

## Capability

`ui.tooltip` is required.

If missing, compile fails with:

`Capability missing: ui.tooltip is required to use 'tooltip' components. Add 'capability is ui.tooltip' to the manifest.`

## Syntax

Standalone form:

```ai
spec is "1.0"

capabilities:
  ui.tooltip

page "Help":
  tooltip "Blend retrieval modes." for "Semantic weight"
```

Embedded form on sliders:

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
    help is "Blend retrieval modes."
```

## Validation

- Tooltip text cannot be empty.
- Duplicate tooltips attached to the same control label are compile-time errors.

## Determinism

- Expand/collapse state is explicit (`collapsed_by_default`).
- No viewport-probing or auto-positioning heuristics are used.
- Tooltip IDs are stable manifest IDs.
