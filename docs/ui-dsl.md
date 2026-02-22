# UI DSL

This is the authoritative description of the UI DSL. It is semantic and explicit. There is no styling DSL or custom CSS; visual control is limited to curated theme tokens.

## 1) What UI DSL is
- Declarative, semantic UI that maps to flows and records.
- Deterministic structure; no per-component styling knobs beyond limited theme tokens when `ui_theme` is enabled.
- Canonical serialization: UI manifests and their IR nodes use stable ordering and deterministic JSON.
- Parser updates are deterministic; incremental parsing must match full-parse output for the UI DSL surface.
- The generated parser is the single runtime parser path for UI DSL processing; legacy parser flags are not supported.
- Frozen surface: additive changes only, no silent behavior changes.
- Text-first: intent over pixels.
- Studio panels (Setup, Graph, Traces, Memory, etc.) are tooling views; they are not part of the UI DSL contract.
- Studio renders the same UI manifest intent as `n3 ui` and does not add DSL semantics.
- Console editing is a file-backed workflow; it writes the same `.ai` constructs a text editor writes and does not add hidden grammar behavior.
- Run modes are explicit and deterministic: `n3 run` renders production UI, `n3 run studio` renders Studio-instrumented UI.
- Preset-driven UI shells (for example `use preset "rag_chat":` and `use preset "agent_workspace":`) are compile-time expansions; run `n3 expand app.ai` to inspect the exact generated UI/flow program.
- `agent_workspace` controlled mode supports deterministic flow overrides for: `agent.route`, `agent.retrieve`, `agent.answer`, `agent.tool_policy`, `agent.fallback`, and `agent.citations.format`.
- Preset override precedence is deterministic: overridden flow bodies are emitted for listed flows; non-overridden flows keep preset defaults while canonical contracts remain stable.

## 2) Core blocks and naming rules
- `ui:` (optional global settings; order inside the block is free)
- `page "name":`
- `flow "name":`
- `record "name":`
- `ai "name":`
- `tool "name":`
- `ui_pack "name":`
- `pattern "name":`
- `responsive:` (optional global breakpoint layout metadata)
- `use plugin "name"` (top-level plug-in declaration for custom UI components)
- `policy`
Rule: use `keyword "name"`; never `keyword is "name"`.
- Reserved words may only be used as identifiers when escaped with backticks (for example `title`).

### Optional grouping syntax
- Grouping delimiters are optional convenience wrappers for short declarations.
- Supported list form: `labels: [bug, feature]` (also `sources`, `capabilities`, `packs`, `only`, `allow override`).
- Supported compact block form: `record "User": { id number, name text }`, `fields: { id is text, total is number }`, `parameters: { heading is text }`.
- Commas are required between grouped entries.
- Nested grouping is not allowed (for example `[a, {b}]`).
- Grouped forms are single-line only in parser input. Multi-line grouped forms must be written using indentation.
- Route paths keep existing placeholder braces (`/api/users/{id}`); this is unrelated to grouping syntax.

## 2.1) Policy declarations
Policy is a declarative, top-level block in `app.ai` that controls ingestion/review/retrieval actions. Order is irrelevant and no expressions are allowed.

Example:
```
policy
  allow ingestion.run
  allow ingestion.review
  require ingestion.override with ingestion.override
  require ingestion.skip with ingestion.skip
  require retrieval.include_warn with retrieval.include_warn
  require upload.replace with upload.replace
```

Rules:
- Each policy action may appear only once.
- `allow` and `deny` take only the action name.
- `require` must include a `with` list of one or more permission names.
- Allowed actions: `ingestion.run`, `ingestion.review`, `ingestion.override`, `ingestion.skip`, `retrieval.include_warn`, `upload.replace`.

## 3) Allowed UI elements
### Page layout slots
Pages may declare an optional `layout:` block to place items into fixed slots.

Allowed slots:
- `header`
- `sidebar_left`
- `main`
- `drawer_right`
- `footer`
- `diagnostics` (special diagnostics-only block inside `layout:`)

Rules:
- Slot evaluation order is fixed: `header` -> `sidebar_left` -> `main` -> `drawer_right` -> `footer`.
- Only the slot names above are valid.
- A slot may be omitted or left empty.
- `diagnostics:` content is diagnostics-only and not part of product layout rendering.
- If `layout:` is present, page items must be declared inside slots (no mixed top-level page items).
- Duplicate slot declarations are compile-time errors.
- Without `layout:`, pages use the legacy vertical `elements` stack.

### Layout containers and conditionals (ui_layout)
Layout primitives and conditional rendering require capability `ui_layout`.

Layout containers:
- `stack:` vertical layout container. Children are any page items.
- `row:` horizontal layout container. Children are any page items.
- `col:` column container for use inside `row:` or other layout containers.
- `grid columns is <positive integer>:` grid layout with fixed column count.
- `sidebar_layout:` container that must include `sidebar:` and `main:` blocks.
- `drawer title is "<text>" when is <boolean>:` layout drawer that opens when the condition is true.
- `sticky top:` / `sticky bottom:` sticky containers that pin to the top or bottom of their scroll area.

Conditionals:
- `show_when is <boolean>` metadata on any UI block.
- `if <boolean>:` with optional `else:` to render alternate children.

Rules:
- `sidebar_layout` must include both `sidebar:` and `main:` blocks.
- `drawer title is ... when is ...` is required for layout drawers.
- `drawer` blocks may appear only at the top level or inside `sidebar_layout main`.
- `grid columns is <n>` requires a positive integer.
- `else:` must immediately follow an `if` block.

Example:
```ai
capabilities:
  ui_layout

page "Layout Demo":
  stack:
    row:
      col:
        text is "Column 1"
      col:
        text is "Column 2"

  sidebar_layout:
    sidebar:
      section "Sources":
        text is "Sidebar"
    main:
      if state.ready:
        text is "Ready"
      else:
        text is "Preparing"

      drawer title is "Details" when is state.show_details:
        text is "Drawer content"

  sticky bottom:
    text is "Sticky footer"
```

Example:
```ai
flow "reply":
  return "ok"

page "Support Inbox":
  layout:
    header:
      title is "Support Inbox"
    sidebar_left:
      section "Folders":
        text is "Open"
    main:
      section "Messages":
        chat:
          messages from is state.messages
          composer calls flow "reply"
    drawer_right:
      section "Details":
        text is "Select a message."
    footer:
      text is "Powered by Namel3ss"
    diagnostics:
      section "Trace":
        text is "Trace output"
```

### Theme tokens (ui_theme)
Theme token overrides require capability `ui_theme`.

Page-level tokens:
- `page "Name" tokens:` followed by token lines, or
- `tokens:` as the first block inside a page.

Tokens (closed enums):
- `size`: `compact` | `normal` | `comfortable`
- `radius`: `none` | `sm` | `md` | `lg` | `full`
- `density`: `tight` | `regular` | `airy`
- `font`: `sm` | `md` | `lg`
- `color_scheme`: `light` | `dark` | `system` (page-only)

Per-component overrides:
- Inside any component block, you may declare `size is "<value>"`, `radius is "<value>"`, `density is "<value>"`, or `font is "<value>"`.
- `color_scheme` is only allowed at the page level.

Settings page:
- `include theme_settings_page` inserts a built-in settings page that writes to `state.ui.settings.<token>`.

Rules:
- Tokens must be declared immediately after the page header.
- Duplicate token definitions at the same level are parse errors.
- Invalid values fail at parse time with allowed values listed.
- Using tokens or `include theme_settings_page` without `ui_theme` raises a compile error.

Example:
```ai
capabilities:
  ui_theme

flow "run_action":
  return "ok"

page "Theme Demo" tokens:
  size is "compact"
  radius is "lg"
  density is "regular"
  font is "sm"
  color_scheme is "system"

  section "Controls":
    button "Run":
      size is "comfortable"
      calls flow "run_action"

  include theme_settings_page
```

### RAG UI pattern (ui_rag)
`rag_ui` is a deterministic, compiler-expanded RAG shell that produces a standard layout using existing layout primitives.

Rules:
- Using `rag_ui` requires capability `ui_rag`.
- `rag_ui` must be the only page body entry.
- Bases: `assistant`, `evidence`, `research`.
- Features: `conversation`, `evidence`, `research_tools`.
- Conversation defaults include deterministic `chat.stream_state` for replay-safe streaming status.
- `binds:` is optional.
- Missing state binds default deterministically by feature:
  - `conversation`: `on_send -> flow "ask_question"`, `messages -> state.chat.messages`
  - `evidence`: `citations -> state.chat.citations`
  - `research_tools`: `scope_options -> state.chat.scope_options`, `scope_active -> state.chat.scope_active`
- Allowed slots: `header`, `sidebar`, `drawer`, `chat`, `composer`.
- Theme token overrides (size, radius, density, font, color_scheme) may appear inside `rag_ui` and apply after runtime settings.

Example:
```ai
# doc:skip rag_ui example (phase 3)
capabilities:
  ui_rag
  ui_theme

flow "answer_question":
  ask ai "assistant" with stream: true and input: "Hello" as reply
  return reply

flow "ingest_latest":
  return "ok"

page "RAG Shell":
  rag_ui:
    base is "evidence"
    features: conversation, evidence
    size is "compact"
    radius is "lg"
    color_scheme is "system"

    binds:
      messages from is state.chat.messages
      on_send calls flow "answer_question"
      citations from is state.chat.citations
      thinking when is state.loading
      drawer_open when is state.ui.show_drawer
      source_preview from is state.ui.preview_source
      ingest_flow calls flow "ingest_latest"

    slots:
      sidebar:
            section "Sources":
              text is "Custom sidebar"
```

Minimal research shell (<10 lines of code):
```ai
spec is "1.0"
capabilities:
  ui_rag
flow "ask_question":
  return "ok"
page "RAG":
  rag_ui:
    base is "research"
```

Structural:
- `section "Label":` children: any page items.
- `card_group:` children: `card` only.
- `card "Label":` children: any page items plus `stat`/`actions` blocks.
- `tabs:` children: `tab` only (optional `default is "Label"`).
- `tab "Label":` children: any page items.
- `modal "Label":` page-level overlay container.
- `drawer "Label":` page-level overlay container.
- `include theme_settings_page` inserts a built-in theme settings panel (requires `ui_theme`).
- `chat:` children: chat elements only (`messages`, `composer`, `thinking`, `citations`, `trust_indicator`, `source_preview`, `scope_selector`, `memory`).
  - Optional chat settings inside `chat:`:
    - `style is "bubbles"|"plain"` (default `bubbles`)
    - `show_avatars is true|false` (default `false`)
    - `group_messages is true|false` (default `true`)
    - `actions are [copy, expand, view_sources]` (default `[]`)
    - `streaming is true|false` (default `false`)
    - `attachments are true|false` (default `false`)
- `row:` children: only `column` (legacy). Use `row` + `col` when `ui_layout` is enabled.
- `column:` children: any page items (legacy).
- `col:` children: any page items (`ui_layout` only).
- `grid:` responsive container with deterministic column spans.
- `divider`

Content:
- `title is "Text"`
- `text is "Text"`
- `image is "<media_name>"`
- `loading [variant: spinner|skeleton]`
- `snackbar message: "..." duration: <ms>`
- `icon name: "<icon>" size: small|medium|large role: decorative|semantic [label: "..."]`
- `lightbox images: ["a.png", "b.png"] [startIndex: <n>]`
- `badge from state.<path> [style is "neutral"|"success"|"warning"]` read-only status badge; text is rendered from the bound state value.

Data/UI bindings:
- `form is "RecordName"` auto-fields from record; optional `groups`/`help`/`readonly`; submits as `submit_form` action.
- `table is "RecordName"` displays records; optional `columns`/`empty_state`/`sort`/`pagination`/`selection`/`row_actions`.
- `table from state <path>` displays a read-only table from state; requires `columns` with `include` entries; no sort, pagination, selection, or row actions.
- `list is "RecordName"` displays records; optional `variant`/`item` mapping/`empty_state`/`selection`/`actions`.
- `list from state <path>` displays a read-only list from state; requires an `item` mapping; no selection or actions.
- `chart is "RecordName"` or `chart from is state.<path>` read-only visualization (`summary`/`bar`/`line`), optional `type`/`x`/`y`/`explain`; must be paired with a table or list using the same data source.
- `messages from is state.<path>` renders a message list from state (role/content).
- `composer sends to flow "flow_name"` emits a `call_flow` action with `message` payload.
- `composer sends to flow "flow_name"` may declare extra fields with a `send` block; indented lines inherit `send` to avoid repetition.
- `input text as <name>` with body `send to flow "<flow>"` renders a single-line input and emits a `call_flow` action with payload named `<name>`; the flow must declare a matching text input field (flow input block or contract).
- `thinking when is state.<path>` UI-only indicator bound to state.
- `thinking when state.<path>` is also accepted (equivalent to `thinking when is ...`).
- `citations from state.<path>` renders citation chips with deterministic numbering; each citation requires `title` and `url` or `source_id`.
- Legacy `citations from is state.<path>` remains available inside `chat` as the debug-only citations panel.
- `source_preview from <source_id|state.<path>>` renders a source preview card/drawer payload.
- `trust_indicator from state.<path>` renders a trust badge from a boolean or score in `[0, 1]`.
- `scope_selector from state.<options_path> active in state.<active_path>` renders selectable retrieval scopes and emits `scope_select`.
- `memory from is state.<path> [lane is "my"|"team"|"system"]` display-only memory list from state.
- `upload <name>` declares an upload request (intent-only). Optional `accept` list and `multiple` flag.
- `ingestion_status` is a runtime-manifest element (not a DSL keyword). When an upload has a matching `state.ingestion[upload_id]` report, Studio renders a status card after the upload element with deterministic `status`, `reasons`, `details`, and optional `fallback_used`.
- `runtime_error` is a runtime-manifest element (not a DSL keyword). When runtime emits normalized errors, Studio renders category, message, hint, origin, and stable code.
- `button "Label":` `calls flow "flow_name"` creates `call_flow` action.
- `link "Label" to page "PageName"` navigates to a named page; emits an `open_page` action.
- `use ui_pack "pack_name" fragment "fragment_name"` static expansion of a pack fragment.
- `use pattern "pattern_name"` static expansion of a UI pattern.
- Custom component tags are allowed only when declared by a loaded plug-in (`use plugin "name"`).
- Optional metadata: `debug_only` can be set on pages and UI items (`debug_only is true|false|"trace"|"retrieval"|"metrics"`).
- Optional page metadata: `diagnostics is true|false` marks a diagnostics-only page.
- Record/flow names may be module-qualified (for example `inv.Product`, `inv.seed_item`) when using Capsules.

Custom component example:
```
use plugin "maps"

page "dashboard":
  MapViewer lat: state.user.location.lat lng: state.user.location.lng zoom: 12 onClick: OpenLocationDetails
```

Rules:
- Unknown component tags still fail unless a loaded plug-in provides that component.
- Component property names and types are validated against the plug-in schema.
- Event properties (for example `onClick`) must reference known flow names.
- Plug-ins are capability-gated: add `custom_ui` and `sandbox` in the app `capabilities` block.
- Permissioned or hook-enabled community extensions additionally require `extension_trust` (and `extension_hooks` when `hooks` are declared in the manifest).
- Plug-in discovery uses `N3_UI_PLUGIN_DIRS` (path-separated list), then project defaults:
  - `<project_root>/.namel3ss/ui_plugins`
  - `<project_root>/ui_plugins`
  - `<project_root>/plugins`

Structured composer:
```
page "home":
  chat:
    composer sends to flow "ask"
      send category as text
          language as text
```
Rules:
- Message is always included.
- Extra fields are text-only today.
- Flow inputs must match `message` plus the declared extra fields.
- Payload field order follows the declaration order.

Enhanced chat example:
```ai
capabilities:
  streaming

flow "answer_question":
  ask ai "assistant" with stream: true and input: "Hello" as reply
  return reply

page "assistant":
  chat:
    style is "bubbles"
    show_avatars is true
    group_messages is true
    actions are [copy, expand, view_sources]
    streaming is true
    attachments are true
    messages from is state.chat.messages
    composer calls flow "answer_question"
    thinking when state.chat.thinking
```

Nesting rules:
- `row` -> `column` only (legacy). `row` + `col` requires `ui_layout`.
- `chat` -> `messages`, `composer`, `thinking`, `citations`, `trust_indicator`, `source_preview`, `scope_selector`, `memory` only.
- `tabs` -> `tab` only; `tab` is only valid inside `tabs`.
- `modal`/`drawer` are page-level only; they are opened/closed via actions.
- `drawer title is ... when is ...` may appear only at the top level or inside `sidebar_layout main`.
- `card_group` -> `card` only.
- Others may contain any page items.
- Pages remain declarative: no let/set/match inside pages. `if` blocks are allowed when `ui_layout` is enabled.

Show blocks:
- `show` can group tables and lists under one verb using indentation.
- `show` only supports `table` and `list` entries.
- Example:
```
page "home":
  show table from state matches
       list from state selected
```

UI packs:
- `ui_pack` declares a version and one or more fragments.
- Fragments contain UI items only (no flows, tools, or records).
- `use ui_pack` is static expansion; origin metadata is preserved in manifests.
- Packs are static: no parameters, conditionals, or dynamic loading.

UI patterns:
- `pattern` declares reusable UI items with optional parameters.
- Patterns contain UI items only (no flows, tools, or records).
- `use pattern` is static expansion; origin metadata includes pattern name, invocation, element mapping, and parameter values.
- Patterns are deterministic and additive; no runtime composition or branching.

## 3.3) Patterns
Patterns are a build-time reuse mechanism for UI items.

Declaration:
```
pattern "Empty State":
  parameters:
    heading is text
    guidance is text
    action_label is text optional
    action_flow is text optional
  section:
    title is param.heading
    text is param.guidance
    button param.action_label:
      calls flow param.action_flow
```

Invocation:
```
page "home":
  use pattern "Empty State":
    heading is "No results"
    guidance is "Try again"
    action_label is "Retry"
    action_flow is "retry_search"
```

Rules:
- Parameters are declared in a `parameters:` block and must be one of `text`, `number`, `boolean`, `record`, or `page`.
- Defaults are literal values only; optional parameters may be omitted.
- Inside patterns, reference parameters as `param.<name>`.
- Pattern arguments are literal values only (text/number/boolean or record/page identifiers); no expressions or state paths.
- Expansion is static and deterministic; UI manifests record pattern origin metadata.

Built-in patterns:
- `Loading State` (params: `intent` text, `message` text)
- `Empty State` (params: `heading` text, `guidance` text, optional `action_label`/`action_flow`)
- `Error State` (params: `heading` text, `message` text, optional `action_label`/`action_flow`)
- `Results Layout` (params: `record_name` record, optional `layout` text, optional `filters_title`/`filters_guidance`, optional empty-state params `empty_title`, `empty_guidance`, `empty_action_label`, `empty_action_flow`)
- `Status Banner` (params: `tone` text, `heading` text, optional `message` text, optional `action_label`/`action_flow`)

## 3.4) Navigation
Navigation can be declared as state-driven in the global `ui:` block.

Example:
```
ui:
  pages:
    active page:
      is "home" only when state.page is "home"
      is "results" only when state.page is "results"
```

Rules:
- `active page` appears once inside `ui: pages:`.
- Each rule uses `is "<page>" only when state.<path> is <literal>`.
- Rules are evaluated in source order; the first match wins.
- If no rule matches, the first declared page is selected.
- State paths use dot notation only.
- Text literals are quoted; numbers and booleans are unquoted.
- Unknown page names and undeclared state paths are build-time errors.
- When `active page` is present, state selects the page and the UI reflects it.

## 3.1) Media
- Media assets live in a locked `media/` folder at the app root (next to app.ai).
- References use the base name only (no extensions, no paths).
- Allowed formats: `.png`, `.jpg`/`.jpeg`, `.svg`, `.webp`.
- Image role is semantic only; runtime controls layout/accessibility:
  - `image is "welcome":`
    `role is "hero"`
- Roles must be one of: `iconic`, `illustration`, `hero`.
- No other image attributes are supported.
- Missing media behavior:
  - `n3 check` -> warning + suggestions
  - `n3 build` -> error + suggestions
  - runtime -> placeholder intent with `fix_hint`

## 3.2) Visibility
- Optional `visible when <expr>` may be appended to any page item, `tab` header, or page header.
- Backward-compatible aliases remain supported: `visibility is <expr>`, `when is <expr>`, and `visible_when: <expr>`.
- Optional `only when <expr>` may be declared as a single indented line inside a page item block (or directly under a single-line item).
- Optional `debug_only is true|false|"trace"|"retrieval"|"metrics"` may be appended to page items, and `debug_only: true|false|"trace"|"retrieval"|"metrics"` may be declared at page scope.
- Optional page metadata `diagnostics is true|false` marks a diagnostics-only page.
- In pages with `layout:`, `diagnostics:` is a diagnostics-only content block.
- Text literals use quotes; numbers and booleans are unquoted.
- A declaration may use only one visibility clause (`visible when` or an alias). Duplicate clauses are a parse error.
- `only when` cannot be combined with inline visibility clauses on the same item.
- Visibility expressions support:
  - state paths (`state.user.role`)
  - literals (`"admin"`, `true`, `3`)
  - comparisons (`==`, `!=`, `>`, `<`, `>=`, `<=`)
  - boolean logic (`and`, `or`, `not`)
  - membership (`in`, `not in`) with list literals (`["ready", "queued"]`)
- Function calls and side effects are not allowed in visibility expressions.
- For plain `state.<path>` visibility clauses, a path is visible only when the state value exists and is truthy.
- For `only when`, missing state paths or type mismatches fail at build time.
- Page-level visibility is evaluated before page layout. If false, the page is omitted from the manifest and navigation.
- In Studio display mode (`display_mode: studio`), diagnostics are off by default: hidden items, diagnostics pages, and `debug_only` items/actions are filtered.
- When diagnostics are enabled, hidden elements remain in the manifest with `visible: false` and diagnostics/debug-only pages, blocks, and actions are included.
- In production mode, hidden elements are omitted from the emitted manifest.
- Elements and pages with `debug_only: true` are omitted unless diagnostics mode is enabled.
- Pages with `diagnostics is true` and `layout.diagnostics` blocks are omitted unless diagnostics mode is enabled.
- Backward-compatibility: internal callers that omit `display_mode` keep diagnostics enabled to preserve older manifest contracts.
- `n3 run --diagnostics <app.ai>` enables diagnostics rendering outside Studio for local debugging.
- UI explain output includes the predicate, referenced state paths, evaluated result, and the visibility reason.

## Warning pipeline and guardrails
- UI warnings are produced during manifest construction in this fixed order:
  - `layout`
  - `upload`
  - `visibility`
  - `diagnostics`
  - `copy`
  - `story_icon`
  - `consistency`
- Each stage uses stable sorting by code and location so warning order is deterministic for the same `.ai` source.
- Warnings surface in:
  - `n3 app.ai ui --json` -> `manifest.warnings`
  - `/api/ui` -> `manifest.warnings`
  - `/api/ui/manifest` -> `manifest.warnings`
  - `/api/ui/actions` and `n3 app.ai actions --json` -> `warnings`
  - Studio Errors panel -> `UI warnings` card
- Guardrail baselines are snapshot-tested with:
  - `python -m pytest -q tests/ui/test_ui_manifest_baseline.py tests/ui/test_warning_pipeline.py`

## 3.5) Responsive layout
- Declare top-level breakpoints with:
```
responsive:
  breakpoints:
    mobile: 0
    tablet: 640
    desktop: 1024
```
- Sections can declare responsive spans: `section "Overview" columns: [12, 6, 4]:`
- `grid` requires `columns` in its block:
```
grid:
  columns: [12, 6, 4]
  card:
    title is "Item"
```
- `columns` values are deterministic integer spans. Each value must be `1..12`.
- If fewer spans are provided than breakpoints, the last span is repeated.
- If `responsive_design` capability is absent, responsive spans fall back to the first value (legacy static layout).

Example:
```
page "home":
  title is "Results" when is state.results.ready
  section "Results" visible_when is state.results.present:
    table is "Result"
  text is "Loading"
    only when state.status is "loading"
  button "Delete":
    calls flow "DeleteRecord"
    only when state.user.role == "admin" and state.task.status in ["ready", "queued"]
```

## 3.3) Status patterns
Status blocks provide built-in loading/empty/error patterns that render before normal UI.

Grammar:
```
page "home":
  status:
    loading when state.status is "loading"
      text is "Loading"

    empty when state.items is empty
      text is "No results"

    error when state.status is "error"
      text is "Something went wrong"
```

Rules:
- Only one `status` block may appear per page.
- Status names must be `loading`, `empty`, or `error`.
- Conditions use `state.<path> is <literal>` or `state.<path> is empty` only.
- Empty checks only apply to list/map values; other types fail at build time.
- Status blocks evaluate before normal UI blocks.
- If exactly one status matches, only that block renders.
- If none matches, the normal page UI renders.
- If more than one matches, build fails with a deterministic error.

## 4) Data binding & actions
- Forms bind to records; payload is `{values: {...}}`.
- Buttons call flows by name; links navigate to pages; actions are deterministic (`call_flow`, `submit_form`, `open_page`).
- Overlays open/close via actions (`open_modal`, `close_modal`, `open_drawer`, `close_drawer`).
- Chat elements bind to explicit state paths; list ordering is preserved as provided.
- Composer submissions call flows and include `{message: "<text>"}` plus any declared extra fields in the same payload.
- Text input submissions call flows and include `{<name>: "<text>"}` in payload; empty inputs do not emit actions.
- UI-only state (selection, tabs active, modal/drawer open) never triggers flows.
- State is visible in Studio; UI manifest lists actions and elements with stable IDs.

## 4.1) Action availability
- Actions can declare a single availability rule nested under the action line.
- Availability uses equality only and accepts literal text in quotes, number, or boolean values.
- Availability is separate from visibility; it disables the action without hiding it, and disabled actions are rejected at runtime.

Example:
```
page "home":
  button "Submit":
    calls flow "submit_flow"
      only when state.status is "ready"
```

## 4.2) UI explanation output
- The ui manifest can be explained with `n3 see`.
- Output is deterministic, bounded, and lists pages, elements, bindings, and action availability.
- Pack origin metadata is included when elements are expanded from a `ui_pack`.

## 4.3) Upload requests
- `upload <name>` declares intent to request a file from the user.
- Uploads are request-only; no upload occurs until runtime bindings are provided.
- When a file is selected, the client posts bytes to `/api/upload` and uses the returned metadata to update state.
- Runtime records selections under `state.uploads.<name>` as a map of `{upload_id: {id, name, size, type, checksum}}`.
- Upload selection is metadata-only; ingestion runs only when explicitly triggered.
- Optional block fields:
  - `accept is "application/pdf,image/png"` or `accept is "pdf", "png"` (MIME list / shorthand extensions)
  - `multiple is true|false` (defaults to false)
  - `required is true|false` (defaults to false; gates flow execution when `state.uploads.<name>` is read)
  - `label is "<button text>"` (defaults to `"Upload"`)
  - `preview is true|false` (defaults to false; shows built-in preview summary for image/text/pdf metadata)
- When `multiple` is false, a new file replaces the existing selection.
- Upload widgets include built-in remove/clear actions and deterministic file ordering.
- Manifests include:
  - upload element fields: `type`, `name`, `accept`, `multiple`, `required`, `label`, `preview`, `files`
  - top-level `upload_requests` entries with the same deterministic request contract
- Warnings are deterministic:
  - `upload.missing_control` when uploads capability is enabled but no upload control is declared
  - `upload.unused_declaration` when an upload declaration is never referenced from `state.uploads.<name>`

## 4.4) Retrieval tuning controls (Studio)
- Retrieval tuning uses normal flow calls and does not add new UI DSL syntax.
- Supported runtime tuning flows are:
  - `set_semantic_k(<int>)`
  - `set_lexical_k(<int>)`
  - `set_final_top_k(<int>)`
  - `set_semantic_weight(<number in [0, 1]>)`
- Studio may render interim controls (dropdowns/radios) when these flows exist with valid one-field numeric contracts.
- Production behavior is unchanged: if these flows are not defined, retrieval keeps legacy defaults.
- Control metadata and any disabled reasons are deterministic and emitted in canonical manifest order.

## 5) Core UI primitives
- `page "<title>":` container with optional `purpose is "<string>"` metadata (page-only; deterministic id generation). Duplicate page titles are rejected.
- `purpose is "<string>"` may only appear at the page root; it is persisted to manifests and Studio payloads as metadata for runtime decisions.
- `number:` deterministic numeric intent (runtime-owned visuals; no sizing):
  - Phrase form: unquoted or quoted phrases (e.g., `active users`, `"revenue today"`).
  - Aggregate form: `count of "<record>" as "<label>"` (record must exist; suggestions on typos).
  - Stable ordering and stable entry ids; no manual styling.
- `view of "<record>":`
  - Record must exist (suggestions on typos).
  - Runtime selects representation deterministically today: records with three or fewer fields render as list/cards; otherwise as table.
  - Defaults are runtime-owned: deterministic column order (record field order), default ordering by the record id field, stable empty-state/paging defaults.
- `compose <name>:` semantic grouping (no layout positioning). Name must be an identifier, not reserved, unique within a page. Children are supported primitives; order is preserved.

## 6) Story progression
- `story "<title>"` inside pages or `compose` blocks describes a deterministic progression of steps.
- Simple form:
  - Each quoted line is a step title in written order.
  - Default progression is sequential; the last step finishes without routing.
- Advanced form:
  - `step "<title>":` with optional fields (no extras allowed):
    - `text is "<string>"`
    - `icon is <icon_name>`
    - `image is "<media_name>"` (optional `role is "iconic" | "illustration" | "hero"` block)
    - `tone is "<tone>"`
    - `requires is "<string>"`
    - `next is "<step title>"`
- Validation rules:
  - Step titles must be unique within a story; unknown `next` targets suggest fixes.
  - Cycles are rejected with a clear path.
- Tone must be one of: `informative`, `success`, `caution`, `critical`, `neutral`.
- Icons are runtime-owned and validated against a closed registry (lowercase snake_case). Use `n3 icons` to list available names.
- Icons are intent-only: runtime applies tint based on theme + tone + state (no user-specified colors). SVGs are monochrome and use `currentColor`; custom uploads are not supported.
- Built-in icon assets are bundled under `resources/icons/` for engine use; no custom icon references are supported.
- `requires` is declarative gating; when it references `state.<path>`, readiness is derived from state when available and is explainable in manifests and Studio.
- Manifest contract:
  - Stable ids for stories and steps derived from page/story/step titles.
- Step order is preserved; default `next` links follow written order unless overridden.
- Gates carry `requires`, optional `state` path, and readiness (`ready` is `true`/`false`/`null` when not evaluated).

## 7) Flow actions
- Declarative grammar (no colon form in this surface):
  - `flow "<name>"`
    `<steps...>`
- Names: unique and non-reserved identifiers.
- Supported steps (closed set):
  - `input` block: `input` then `<field> is <type>`; input fields are unique and types are validated.
  - `require "<condition>"` (string gate; no expression language in this surface).
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
  - Ordering and keep first statements; those belong to normal flows, not UI DSL actions.
  - Ask AI and structured AI input statements; those belong to normal flows, not UI DSL actions.
  - Orchestration (fan-out/fan-in), merge policies, or flow/pipeline calls.
- Triggering from UI:
  - `button "Label":` use `calls flow "<name>"` to bind to a flow.
  - Unknown flow references error with fix hints; runtime surfaces disabled affordance if requirements are unmet.
- Flow actions run normal flows; those flows may enqueue background jobs or invoke backend capabilities when explicitly enabled.

## 8) Global UI settings
- Grammar (keys may appear in any order; output is normalized deterministically):
  - `ui`:
    - `theme is "<theme>"`
    - `accent color is "<accent>"`
    - `density is "<density>"`
    - `motion is "<motion>"`
    - `shape is "<shape>"`
    - `surface is "<surface>"`
    - visual theme token overrides:
      - `primary_color is "#RRGGBB"`
      - `secondary_color is "#RRGGBB"`
      - `background_color is "#RRGGBB"`
      - `foreground_color is "#RRGGBB"`
      - `font_family is "<font stack>"`
      - `font_size_base is <number>`
      - `font_weight is <number>`
      - `spacing_scale is <number>`
      - `border_radius is <number>`
      - `shadow_level is <integer>`
  - `theme` (top-level, optional, before pages):
    - `preset: "<preset>"`
    - `brand_palette:`
      - `<name>: "<hex-or-css-color>"`
    - `tokens:`
      - `<token.name>: <token.ref-or-color>`
    - `harmonize: true|false`
    - `allow_low_contrast: true|false`
    - design axes: `density`, `motion`, `shape`, `surface`
- Defaults (applied when the ui block is missing):
  - theme: `light`
  - accent color: `blue`
  - density: `comfortable`
  - motion: `subtle`
  - shape: `rounded`
  - surface: `flat`
- Allowed values (closed enums with "did you mean ..." guidance):
  - Themes: `light`, `dark`, `white`, `black`, `midnight`, `paper`, `terminal`, `enterprise`
  - Built-in visual themes for `ui.theme`: `default`, `modern`, `minimal`, `corporate`
  - Accent colors: `blue`, `indigo`, `purple`, `pink`, `red`, `orange`, `yellow`, `green`, `teal`, `cyan`, `neutral`
  - Density: `compact`, `comfortable`, `spacious`
  - Motion: `none`, `subtle` (no layout changes; respects OS reduce-motion)
  - Shape: `rounded`, `soft`, `sharp`, `square`
  - Surface: `flat`, `outlined`, `raised`
- Rules:
  - `ui` remains curated and enum-based. Custom colors live in the top-level `theme` block.
  - Visual token overrides are deterministic and validated by type/range.
  - If `ui.theme` is a visual theme (`default|modern|minimal|corporate`), runtime light/dark setting still comes from app theme/runtime theme state.
  - Theme token merge order is fixed: built-in visual theme first, then explicit `ui` token overrides.
  - No pixel sizes, margins, padding, or per-component styling knobs.
  - Unknown keys/values are rejected with plain-English guidance.
  - Settings are global and appear in CLI and Studio manifests in normalized order.
  - `theme` is deterministic: token derivation order is fixed and contrast checks run at compile time.
  - `brand_palette`, `tokens`, and `harmonize` require capability `custom_theme`.
- Runtime:
  - Theme changes (`set theme to "<theme>"`) use the same allowed themes.
  - `theme_preference` persists overrides when enabled: `allow_override` (true|false), `persist` (`none`|`local`|`file`). Defaults keep runtime overrides disabled and unpersisted.
  - Manifest preference metadata includes a reserved storage key: `namel3ss_theme`.
  - Manifest includes deterministic visual theme metadata: `theme_name`, merged `tokens`, compiled `css`, `css_hash`, and optional `font_url`.
  - Runtime applies theme CSS/tokens without page reload.

### 8.1 Component variants and style hooks
- `button` supports `variant` values: `primary`, `secondary`, `success`, `danger`.
- `card` supports `variant` values: `default`, `elevated`, `outlined`.
- `style_hooks` allow token overrides with a constrained hook set:
  - `button`: `background`, `border`, `text`
  - `card`: `background`, `border`, `text`, `shadow`, `radius`
- Hook values must reference existing theme tokens. Unknown hooks/tokens fail deterministically at compile time.

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
- Advanced routing (guards, parameters, auth)
- Arbitrary per-component styles or raw CSS values (theme tokens are the only styling surface)
- Pixel-perfect layout controls
- Implicit AI calls or memory access from UI elements

## 10) Anti-examples
- `flow is "demo"` (invalid; must be `flow "demo"`)
- `ui: theme is "#121212"` (ui themes are curated names only)
- `theme is "system"` (not a supported theme value)
- `theme_tokens: foo is "bar"` (unknown token)
- `set theme to "dark"` when `allow_override` is false (lint/engine error)

## 11) Compatibility promise
- Spec is frozen; changes must be additive and documented.
- Any change to UI DSL code must update this spec, examples, and tests together.
- `empty_state` may be:
  - indented text block (existing behavior), or
  - inline `hidden`/`false` to suppress rendering when rows are empty.

## 12) GA stability notes
- Public UI DSL contracts are frozen for 1.x and governed by `GOVERNANCE.md`.
- Compatibility and deprecation timelines are tracked in:
  - `docs/compatibility_policy.md`
  - `docs/deprecation_policy.md`
- Studio may expose extra debug surfaces, but production manifests keep deterministic ordering and stable IDs.
