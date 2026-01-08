# UI DSL (v0.1.x) — Spec Freeze

This is the authoritative, frozen description of the UI DSL for v0.1.x. It is semantic and explicit. There is no styling DSL, no CSS, no custom colors.

## 1) What UI DSL is
- Declarative, semantic UI that maps to flows and records.
- Deterministic structure; no per-component styling knobs.
- Frozen surface for v0.1.x: additive changes only, no silent behavior changes.
- Text-first: intent over pixels.
- Studio panels (Setup, Graph, Traces, Memory, etc.) are tooling views; they are not part of the UI DSL contract.

## 2) Core blocks and naming rules
- `page "name":`
- `flow "name":`
- `record "name":`
- `ai "name":`
- `tool "name":`
- `ui_pack "name":`
Rule: use `keyword "name"`; never `keyword is "name"`.

## 3) Allowed UI elements (v0.1.x)
Structural:
- `section "Label":` — children: any page items.
- `card_group:` — children: `card` only.
- `card "Label":` — children: any page items plus `stat`/`actions` blocks.
- `tabs:` — children: `tab` only (optional `default is "Label"`).
- `tab "Label":` — children: any page items.
- `modal "Label":` — page-level overlay container.
- `drawer "Label":` — page-level overlay container.
- `chat:` — children: chat elements only (`messages`, `composer`, `thinking`, `citations`, `memory`).
- `row:` — children: only `column`.
- `column:` — children: any page items.
- `divider`

Content:
- `title is "Text"`
- `text is "Text"`
- `image is "https://..."` (optional `alt`)

Data/UI bindings:
- `form is "RecordName"` – auto-fields from record; optional `groups`/`help`/`readonly`; submits as `submit_form` action.
- `table is "RecordName"` – displays records; optional `columns`/`empty_state`/`sort`/`pagination`/`selection`/`row_actions`.
- `list is "RecordName"` – displays records; optional `variant`/`item` mapping/`empty_state`/`selection`/`actions`.
- `chart is "RecordName"` or `chart from is state.<path>` – read-only visualization (`summary`/`bar`/`line`), optional `type`/`x`/`y`/`explain`; must be paired with a table or list using the same data source.
- `messages from is state.<path>` – renders a message list from state (role/content).
- `composer calls flow "flow_name"` – emits a `call_flow` action with `message` payload.
- `thinking when is state.<path>` – UI-only indicator bound to state.
- `citations from is state.<path>` – display-only citations list from state.
- `memory from is state.<path> [lane is "my"|"team"|"system"]` – display-only memory list from state.
- `button "Label":` `calls flow "flow_name"` – creates `call_flow` action.
- `use ui_pack "pack_name" fragment "fragment_name"` – static expansion of a pack fragment.
- Record/flow names may be module-qualified (for example `inv.Product`, `inv.seed_item`) when using Capsules.

Nesting rules:
- `row` -> `column` only.
- `chat` -> `messages`, `composer`, `thinking`, `citations`, `memory` only.
- `tabs` -> `tab` only; `tab` is only valid inside `tabs`.
- `modal`/`drawer` are page-level only; they are opened/closed via actions.
- `card_group` -> `card` only.
- Others may contain any page items.
- Pages remain declarative: no let/set/if/match inside pages.

UI packs:
- `ui_pack` declares a version and one or more fragments.
- Fragments contain UI items only (no flows, tools, or records).
- `use ui_pack` is static expansion; origin metadata is preserved in manifests.
- Packs are static: no parameters, conditionals, or dynamic loading.

## 4) Data binding & actions
- Forms bind to records; payload is `{values: {...}}`.
- Buttons call flows by name; actions are deterministic (`call_flow`, `submit_form`).
- Overlays open/close via actions (`open_modal`, `close_modal`, `open_drawer`, `close_drawer`).
- Chat elements bind to explicit state paths; list ordering is preserved as provided.
- Composer submissions call flows and include `{message: "<text>"}` in payload.
- UI-only state (selection, tabs active, modal/drawer open) never triggers flows.
- State is visible in Studio; UI manifest lists actions and elements with stable IDs.

## 4.1) UI explanation output
- The ui manifest can be explained with `n3 see`.
- Output is deterministic, bounded, and lists pages, elements, bindings, and action availability.
- Pack origin metadata is included when elements are expanded from a `ui_pack`.

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
  2. session engine theme
  3. app.theme
  4. system pref (only when app.theme is "system")
  5. fallback "light"
- Studio preview override is preview-only; not engine, not persisted.

### Type canon
- Canonical field types: `text`, `number`, `boolean` (and `json` if already supported).
- Legacy aliases accepted today but not canonical: `string` → `text`, `int`/`integer` → `number`, `bool` → `boolean`.
- Use canonical types in new code and docs. Examples below use `text/number/boolean`.
- Tooling may reject aliases when strict types are enabled (e.g., `--no-legacy-type-aliases` or `N3_NO_LEGACY_TYPE_ALIASES=1`); default remains compatible.

Anti-example (not canonical):
```
record "User":
  fields:
    email is string must be present   # use text
    age is int must be greater than 17 # use number
    active is bool must be present     # use boolean
```

## 6) Intentionally missing
- CSS or styling DSL
- Arbitrary routing/navigation
- Per-component styles or custom colors
- Pixel-perfect layout controls
- Implicit AI calls or memory access from UI elements

## 7) Anti-examples
- `flow is "demo"` ❌ (must be `flow "demo"`)
- `theme is "#121212"` ❌ (only light/dark/system)
- `theme_tokens: foo is "bar"` ❌ (unknown token)
- `set theme to "dark"` when `allow_override` is false ❌ (lint/engine error)

## 8) Compatibility promise
- Spec is frozen for v0.1.x → v1.x; changes must be additive and documented.
- Any change to UI DSL code must update this spec, examples, and tests together.
