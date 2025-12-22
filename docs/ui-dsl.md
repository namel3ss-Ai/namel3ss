# UI DSL (v0.1.x) — Spec Freeze

This is the authoritative, frozen description of the UI DSL for v0.1.x. It is semantic and explicit. There is no styling DSL, no CSS, no custom colors.

## 1) What UI DSL is
- Declarative, semantic UI that maps to flows and records.
- Deterministic structure; no per-component styling knobs.
- Text-first: intent over pixels.

## 2) Core blocks and naming rules
- `page "name":`
- `flow "name":`
- `record "name":`
- `ai "name":`
- `tool "name":`
Rule: use `keyword "name"`; never `keyword is "name"`.

## 3) Allowed UI elements (v0.1.x)
Structural:
- `section "Label":` — children: any page items.
- `card "Label":` — children: any page items.
- `row:` — children: only `column`.
- `column:` — children: any page items.
- `divider`

Content:
- `title is "Text"`
- `text is "Text"`
- `image is "https://..."` (optional `alt`)

Data/UI bindings:
- `form is "RecordName"` — auto-fields from record; submits as `submit_form` action.
- `table is "RecordName"` — displays records.
- `button "Label":` `calls flow "flow_name"` — creates `call_flow` action.

Nesting rules:
- `row` -> `column` only.
- Others may contain any page items.
- Pages remain declarative: no let/set/if/match inside pages.

## 4) Data binding & actions
- Forms bind to records; payload is `{values: {...}}`.
- Buttons call flows by name; actions are deterministic (`call_flow`, `submit_form`).
- State is visible in Studio; UI manifest lists actions and elements with stable IDs.

## 5) Theming (Phases 1–5)
- `app: theme is "light"|"dark"|"system"` (default `system`).
- `theme_tokens:` allowed tokens/values (closed):
  - surface: default|raised
  - text: default|strong
  - muted: muted|subtle
  - border: default|strong
  - accent: primary|secondary
- Runtime change: `set theme to "light"|"dark"|"system"` (only if `app.theme_preference.allow_override is true`).
- `theme_preference:` (defaults: allow_override=false, persist="none")
  - `allow_override is true|false`
  - `persist is "none"|"local"|"file"`
- Precedence (initial resolution):
  1. persisted preference (allow_override=true, persist="file")
  2. session runtime theme
  3. app.theme
  4. system pref (only when app.theme is "system")
  5. fallback "light"
- Studio preview override is preview-only; not runtime, not persisted.

### Type canon
- Canonical field types: `text`, `number`, `boolean` (and `json` if already supported).
- Legacy aliases accepted today but not canonical: `string` → `text`, `int`/`integer` → `number`, `bool` → `boolean`.
- Use canonical types in new code and docs. Examples below use `text/number/boolean`.
- Tooling may reject aliases when strict types are enabled (e.g., `--no-legacy-type-aliases` or `N3_NO_LEGACY_TYPE_ALIASES=1`); default remains compatible.

Anti-example (not canonical):
```
record "User":
  field "email" is string must be present   # use text
  field "age" is int must be greater than 17 # use number
  field "active" is bool must be present     # use boolean
```

## 6) Intentionally missing
- CSS or styling DSL
- Arbitrary routing/navigation
- Per-component styles or custom colors
- Pixel-perfect layout controls

## 7) Anti-examples
- `flow is "demo"` ❌ (must be `flow "demo"`)
- `theme is "#121212"` ❌ (only light/dark/system)
- `theme_tokens: foo is "bar"` ❌ (unknown token)
- `set theme to "dark"` when `allow_override` is false ❌ (lint/runtime error)

## 8) Compatibility promise
- Spec is frozen for v0.1.x → v1.x; changes must be additive and documented.
- Any change to UI DSL code must update this spec, examples, and tests together.
