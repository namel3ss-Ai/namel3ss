# Theme Tokens

UI manifests expose a strict theme token contract for consistent light/dark rendering and spacing.

## Contract (`theme.tokens_v2`)

- `mode`: `light` | `dark`
- `colors`: `surface`, `text`, `muted`, `border`, `accent`
- `spacing`: `xs`, `s`, `m`, `l`, `xl`
- `radii`: `s`, `m`, `l`
- `typography`: `font_family`, `font_size_base`, `font_weight`

## Validation

- mode must be `light` or `dark`
- color values must be non-empty strings
- spacing values must be positive numbers
- radii values must be non-negative numbers
- typography fields must match expected types

## Backward compatibility

- legacy token payload remains available as `theme.tokens`
- renderer can fall back to Core defaults when v2 token sections are absent

## Determinism

- token maps are emitted with canonical key ordering
- repeated builds with identical inputs produce byte-identical token payloads

