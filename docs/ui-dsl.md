# UI DSL (v0.1.x) Spec Freeze

This is the authoritative, frozen description of the UI DSL for v0.1.x. It is semantic and explicit. There is no styling DSL, no CSS, no custom colors.

## 1) What UI DSL is
- Declarative, semantic UI that maps to flows and records.
- Deterministic structure; no per-component styling knobs.
- Frozen surface for v0.1.x: additive changes only, no silent behavior changes.
- Text-first: intent over pixels.
- Studio panels (Setup, Graph, Traces, Memory, etc.) are tooling views; they are not part of the UI DSL contract.

## 2) Core blocks and naming rules
- `ui:` (optional global settings; order inside the block is free)
- `page "name":`
- `flow "name":`
- `record "name":`
- `ai "name":`
- `tool "name":`
- `ui_pack "name":`
Rule: use `keyword "name"`; never `keyword is "name"`.

## 3) Allowed UI elements (v0.1.x)
Structural:
- `section "Label":` children: any page items.
- `card_group:` children: `card` only.
- `card "Label":` children: any page items plus `stat`/`actions` blocks.
- `tabs:` children: `tab` only (optional `default is "Label"`).
- `tab "Label":` children: any page items.
- `modal "Label":` page-level overlay container.
- `drawer "Label":` page-level overlay container.
- `chat:` children: chat elements only (`messages`, `composer`, `thinking`, `citations`, `memory`).
- `row:` children: only `column`.
- `column:` children: any page items.
- `divider`

Content:
- `title is "Text"`
- `text is "Text"`
- `image is "https://..."` (optional `alt`)

Data/UI bindings:
- `form is "RecordName"` auto-fields from record; optional `groups`/`help`/`readonly`; submits as `submit_form` action.
- `table is "RecordName"` displays records; optional `columns`/`empty_state`/`sort`/`pagination`/`selection`/`row_actions`.
- `list is "RecordName"` displays records; optional `variant`/`item` mapping/`empty_state`/`selection`/`actions`.
- `chart is "RecordName"` or `chart from is state.<path>` read-only visualization (`summary`/`bar`/`line`), optional `type`/`x`/`y`/`explain`; must be paired with a table or list using the same data source.
- `messages from is state.<path>` renders a message list from state (role/content).
- `composer calls flow "flow_name"` emits a `call_flow` action with `message` payload.
- `thinking when is state.<path>` UI-only indicator bound to state.
- `citations from is state.<path>` display-only citations list from state.
- `memory from is state.<path> [lane is "my"|"team"|"system"]` display-only memory list from state.
- `button "Label":` `calls flow "flow_name"` creates `call_flow` action.
- `use ui_pack "pack_name" fragment "fragment_name"` static expansion of a pack fragment.
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

## 5) Core UI primitives (Phase 2)
- `page "<title>":` container with optional `purpose is "<string>"` metadata (page-only; deterministic id generation). Duplicate page titles are rejected.
- `purpose is "<string>"` may only appear at the page root; it is persisted to manifests and Studio payloads as metadata for runtime decisions.
- `number:` deterministic numeric intent (runtime-owned visuals; no sizing):
  - Phrase form: unquoted or quoted phrases (e.g., `active users`, `"revenue today"`).
  - Aggregate form: `count of "<record>" as "<label>"` (record must exist; suggestions on typos).
  - Stable ordering and stable entry ids; no manual styling.
- `view of "<record>":`
  - Record must exist (suggestions on typos).
  - Runtime selects representation deterministically today: records with three or fewer fields render as list/cards; otherwise as table.
  - Defaults are runtime-owned: deterministic column order (record field order), default ordering by the first field, stable empty-state/paging defaults.
- `compose <name>:` semantic grouping (no layout positioning). Name must be an identifier, not reserved, unique within a page. Children are supported primitives; order is preserved.

## 6) Story progression (Phase 3)
- `story "<title>"` inside pages or `compose` blocks describes a deterministic progression of steps.
- Simple form:
  - Each quoted line is a step title in written order.
  - Default progression is sequential; the last step finishes without routing.
- Advanced form:
  - `step "<title>":` with optional fields (no extras allowed):
    - `text is "<string>"`
    - `icon is <icon_name>`
    - `image is "<media_name>"`
    - `tone is "<tone>"`
    - `requires is "<string>"`
    - `next is "<step title>"`
- Validation rules:
  - Step titles must be unique within a story; unknown `next` targets suggest fixes.
  - Cycles are rejected with a clear path.
  - Tone must be one of: `informative`, `success`, `caution`, `critical`, `neutral`.
  - Icon must be one of: `info`, `check`, `alert`, `flag`, `calendar`, `clock`, `play`, `user`, `spark`, `list`.
  - `requires` is declarative gating; when it references `state.<path>`, readiness is derived from state when available and is explainable in manifests and Studio.
- Manifest contract:
  - Stable ids for stories and steps derived from page/story/step titles.
- Step order is preserved; default `next` links follow written order unless overridden.
- Gates carry `requires`, optional `state` path, and readiness (`ready` is `true`/`false`/`null` when not evaluated).

## 7) Flow actions (Phase 4)
- Declarative grammar (no colon form in this surface):
  - `flow "<name>"`
    `<steps...>`
- Names: unique and non-reserved identifiers.
- Supported steps (closed set for phase 4b):
  - `input` block: `input` then `<field> is <type>`; input fields are unique and types are validated.
  - `require "<condition>"` (string gate; no expression language in this phase).
  - `create "<record>"` with one or more `<field> is <value>` assignments.
  - `update "<record>"` with `where "<selector>"` and a `set` block of assignments.
  - `delete "<record>"` with `where "<selector>"`.
- Binding rules:
  - Values are string/number/boolean literals or `input.<field>` only.
  - Selectors are simple equality checks like `<field> is <literal>`.
  - Record and field references must exist; errors include plain-English fixes.
- Determinism:
  - Step ids derive from flow name + step kind + ordinal position.
  - Step order is preserved; record writes and field order are deterministic.
- Explainability:
  - Flow start and step traces include what ran, why it ran (action id + flow), and what changed.
  - Gates include status and reason when available.
  - No timestamps or random ids in explain traces.
- Not supported:
  - Branching, loops, expressions/functions, or hidden side effects.
- Triggering from UI:
  - `button "Label":` use either `calls flow "<name>"` (existing) or `runs "<name>"` (alias) to bind to a flow.
  - Unknown flow references error with fix hints; runtime surfaces disabled affordance if requirements are unmet.

## 8) Global UI settings (Phase 1)
- Grammar (keys may appear in any order; output is normalized deterministically):
  - `ui`:
    - `theme is "<theme>"`
    - `accent color is "<accent>"`
    - `density is "<density>"`
    - `motion is "<motion>"`
    - `shape is "<shape>"`
    - `surface is "<surface>"`
- Defaults (applied when the ui block is missing):
  - theme: `light`
  - accent color: `blue`
  - density: `comfortable`
  - motion: `subtle`
  - shape: `rounded`
  - surface: `flat`
- Allowed values (closed enums with "did you mean ..." guidance):
  - Themes: `light`, `dark`, `white`, `black`, `midnight`, `paper`, `terminal`, `enterprise`
  - Accent colors: `blue`, `indigo`, `purple`, `pink`, `red`, `orange`, `yellow`, `green`, `teal`, `cyan`, `neutral`
  - Density: `compact`, `comfortable`, `spacious`
  - Motion: `none`, `subtle` (no layout changes; respects OS reduce-motion)
  - Shape: `rounded`, `soft`, `sharp`, `square`
  - Surface: `flat`, `outlined`, `raised`
- Rules:
  - No hex or numeric colors; accent colors are hue names only.
  - No pixel sizes, margins, padding, or per-component styling knobs.
  - Unknown keys/values are rejected with plain-English guidance.
  - Settings are global and appear in CLI and Studio manifests in normalized order.
- Runtime:
  - Theme changes (`set theme to "<theme>"`) use the same allowed themes.
  - `theme_preference` persists overrides when enabled: `allow_override` (true|false), `persist` (`none`|`local`|`file`). Defaults keep runtime overrides disabled and unpersisted.

### Type canon
- Canonical field types: `text`, `number`, `boolean` (and `json` if already supported).
- Legacy aliases accepted today but not canonical: `string` -> `text`, `int`/`integer` -> `number`, `bool` -> `boolean`.
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

## 9) Intentionally missing
- CSS or styling DSL
- Arbitrary routing/navigation
- Per-component styles or custom colors
- Pixel-perfect layout controls
- Implicit AI calls or memory access from UI elements

## 10) Anti-examples
- `flow is "demo"` (invalid; must be `flow "demo"`)
- `theme is "#121212"` (themes are curated names only)
- `theme is "system"` (not a supported theme value)
- `theme_tokens: foo is "bar"` (unknown token)
- `set theme to "dark"` when `allow_override` is false (lint/engine error)

## 11) Compatibility promise
- Spec is frozen for v0.1.x + v1.x; changes must be additive and documented.
- Any change to UI DSL code must update this spec, examples, and tests together.
