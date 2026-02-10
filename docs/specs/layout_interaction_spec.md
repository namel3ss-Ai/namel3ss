# LayoutPrimitives Phase 1 Specification

## Scope
Phase 1 defines grammar, AST/IR, manifest schema, validation, and determinism rules for new UI layout and interaction primitives. Runtime and renderer behavior are intentionally out of scope.

## Capability Gate
- Required capability: `ui.custom_layouts`
- Enabled features:
  - `sidebar`, `drawer`, `sticky`, `scroll area`, `two_pane`, `three_pane`
  - Interaction hooks: `on click`, `keyboard shortcut`, `selected item is state.<path>`
- Fallback behavior:
  - If the capability is missing and Studio/debug mode is not enabled, parsing fails with a validation error:
    - `Feature "<feature>" requires capability "ui.custom_layouts" or Studio mode.`

## Simplified Grammar
The syntax is indentation-first and brace-free.

### Root
```text
page <identifier>:
  ...
```

### State Declarations
```text
state:
  ui.selected_item
  ui.drawer_open
```

State declarations are optional, but all state references must resolve to declared entries.

### Layout Blocks
```text
sidebar:
main:
drawer <left|right> trigger <trigger_id>:
sticky <top|bottom>:
scroll area:
scroll area axis <vertical|horizontal>:
two_pane:
  primary:
  secondary:
three_pane:
  left:
  center:
  right:
```

### Interaction Hooks
```text
on click <action_id>
keyboard shortcut <combo>
selected item is state.<path>
```

### Enhanced Existing Elements
```text
form <name>:
  wizard
  section <name>

table <name>:
  reorderable columns
  fixed header

card <name>:
  expandable
  collapsed

tabs <name>:
  dynamic tabs from state.<path>

media <name>:
  inline crop
  annotation
```

## Nesting Rules
### Allowed
- Layout blocks are only valid under `page`.
- `drawer` may nest in any container except a cycle through repeated `trigger_id`.
- `sticky` can appear in containers, but only with `top` or `bottom`.
- `two_pane` requires exactly `primary` and `secondary`.
- `three_pane` requires exactly `left`, `center`, and `right`.

### Forbidden
- Any layout block outside `page`.
- `sidebar` inside another `sidebar`.
- Duplicate sticky position in the same container.
- `drawer` without `trigger_id`.
- Undefined state reference in `selected item` or `dynamic tabs`.

### Parse-Time Error Contract
- Every parse/validation error includes line and column.
- Format: `[line <n>, col <m>] <message>`
- Examples:
  - `Nested sidebar blocks are not allowed.`
  - `Drawer blocks must declare trigger_id.`
  - `Conflicting sticky position "bottom" in the same container.`
  - `Undefined state reference "state.ui.missing". Declare it in a state: block.`

## AST Contract
New nodes (Phase 1):
- `SidebarNode(children, bindings, line, column)`
- `DrawerNode(side, trigger_id, children, bindings, line, column)`
- `StickyNode(position, children, bindings, line, column)`
- `ScrollAreaNode(axis, children, bindings, line, column)`
- `TwoPaneNode(primary, secondary, bindings, line, column)`
- `ThreePaneNode(left, center, right, bindings, line, column)`
- `FormNode(name, wizard, sections, children, bindings, line, column)`
- `TableNode(name, reorderable_columns, fixed_header, children, bindings, line, column)`
- `CardNode(name, expandable, collapsed, children, bindings, line, column)`
- `NavigationTabsNode(name, dynamic_from_state, children, bindings, line, column)`
- `MediaNode(name, inline_crop, annotation, children, bindings, line, column)`
- `LiteralItemNode(text, bindings, line, column)`
- `StateDefinitionNode(path, line, column)`
- `PageNode(name, states, children, line, column)`

Interaction bindings:
- `InteractionBindings(on_click, keyboard_shortcut, selected_item)`

## IR Contract
IR nodes mirror AST shape and add stable IDs:
- `SidebarIR`, `DrawerIR`, `StickyIR`, `ScrollAreaIR`, `TwoPaneIR`, `ThreePaneIR`
- `FormIR`, `TableIR`, `CardIR`, `NavigationTabsIR`, `MediaIR`, `LiteralItemIR`
- `ActionIR(id, event, node_id, target, line, column)`
- `PageLayoutIR(name, state_paths, elements, actions)`

Stable ID rule:
- `stable_layout_id(page, kind, line, column, path)` where:
  - `page` is slugified page name
  - `path` is declaration-order index path
  - digest uses deterministic SHA-256 truncation

## Manifest Contract
Top-level fields:
- `manifest_version` (`"1.0"`)
- `capabilities` (`["ui.custom_layouts"]`)
- `page` (`{"name": "<page>"}`)
- `state` (ordered array of `{path, default}`)
- `layout` (ordered array of layout/component nodes)
- `actions` (ordered array of click/keyboard actions)

New node types:
- `layout.sidebar`, `layout.main`, `layout.drawer`, `layout.sticky`
- `layout.scroll_area`, `layout.two_pane`, `layout.three_pane`
- `component.form`, `component.table`, `component.card`, `component.tabs`, `component.media`

Defaults (backward-compatible normalization):
- Missing new arrays default to `[]`
- Missing optional scalar fields default to `null` or safe scalar defaults
- Older manifests continue to parse; unknown node kinds are preserved

## Minimal Example
```text
page dashboard:
  sidebar:
    # left pane content

  main:
    sticky bottom:
      form search_form:
        # fields here
```

### Plain-Language Flow
- Developer writes one page with `sidebar` and `main`, plus a bottom `sticky` form.
- Parser builds `PageNode -> SidebarNode + MainNode -> StickyNode -> FormNode`.
- IR lowering assigns stable IDs from page name, source location, and declaration path.
- Manifest lowering preserves declaration order:
  - `layout[0] = layout.sidebar`
  - `layout[1] = layout.main` containing `layout.sticky`
- Runtime (Phase 2) will render fixed bottom composer behavior from the `layout.sticky` contract.

## Realistic Example
```text
page chat_workspace:
  state:
    ui.selected_document
    ui.selected_citation
    ui.sources_drawer_open

  sidebar:
    scroll area:
      tabs document_tabs:
        dynamic tabs from state.ui.selected_document
        on click open_document
        selected item is state.ui.selected_document
        card documents:
          expandable
          text quarterly_review

  main:
    two_pane:
      primary:
        scroll area:
          form chat_thread:
            wizard
            section messages
            text assistant_messages
      secondary:
        sticky bottom:
          form composer:
            keyboard shortcut ctrl+enter
            on click send_message

  drawer right trigger citation_click:
    media source_preview:
      inline crop
      annotation
      selected item is state.ui.selected_citation
      on click open_sources
```

### Plain-Language Flow
- Developer declares three regions: left docs list, central chat panes, right sources drawer.
- `on click open_sources` represents citation-driven drawer opening intent.
- Parser captures bindings and validates every `state.<path>` reference.
- IR lowering emits deterministic `ActionIR` entries for click and keyboard interactions.
- Manifest lowering emits ordered `actions` and `layout` arrays; repeated compilation is byte-for-byte stable.
- Runtime (Phase 2) will interpret `trigger_id` and actions to open the right sources drawer and keep composer sticky at the bottom.

## Determinism Guarantees
- Evaluation order:
  - Containers and children are processed strictly in declaration order.
  - Interaction hooks are attached in source order, then sorted deterministically by `(line, column, event, target, node_id)` for manifest actions.
- Stable identifiers:
  - Node IDs derive from `(page slug, node kind, line, column, path)`.
  - Action IDs derive from `(page slug, event, node_id, target, ordinal)`.
- Manifest ordering:
  - `state`, `layout`, and `actions` preserve deterministic ordering.
- Warning ordering:
  - Validation issues are emitted in deterministic source order.
- Replay semantics:
  - Same manifest + same initial state => same action sequence and state transitions.
- Concurrency:
  - Simultaneous interactions are serialized by deterministic action order (no nondeterministic fan-out).
- Error handling:
  - Parse, validation, and runtime-contract errors are explicit and never silent.
  - Error payloads always include line/column when source-linked.
- Prod vs Studio:
  - Capability checks are bypassed only in Studio/debug mode; production requires `ui.custom_layouts`.

## Phase 1 Implementation Notes
- No renderer/runtime execution logic was added.
- Files are split by responsibility and remain under 500 lines each.
- Tests include happy paths, failure modes, determinism checks, and ordering snapshots.
