# New Layout Primitives Tutorial

This tutorial shows how to use the Phase 2 layout and interaction primitives end to end:

- `sidebar`
- `drawer`
- `sticky`
- `scroll area`
- `two_pane` and `three_pane`
- `on click`, `keyboard shortcut`, and `selected item`

## Capability

Advanced layouts require the `ui.custom_layouts` capability.

- Runtime mode: required.
- Studio mode: optional for local iteration and debugging.

If a page uses custom layout primitives without this capability in runtime mode, manifest validation fails with a clear error.

## Minimal example

```namel3ss
page dashboard:
  sidebar:
    text left_pane

  main:
    sticky bottom:
      form search_form:
        section filters
        on click run_search
        keyboard shortcut ctrl+enter
```

What happens:

1. The parser builds a page AST with `sidebar`, `main`, `sticky`, and `form` nodes.
2. The IR lowerer assigns stable IDs from page name, node type, source location, and declaration path.
3. The layout manifest builder emits ordered `elements`, `actions`, and initial `layout_state`.
4. The renderer maps layout nodes to deterministic DOM structures and action handlers.

## RAG chat layout example

```namel3ss
page rag_chat:
  state:
    ui.selected_document
    ui.selected_citation

  sidebar:
    scroll area:
      tabs documents:
        dynamic tabs from state.ui.selected_document
        selected item is state.ui.selected_document
        on click open_document
        card library:
          expandable
          text available_documents

  main:
    two_pane:
      primary:
        scroll area:
          text conversation
      secondary:
        sticky bottom:
          form composer:
            section prompt
            on click send_message
            keyboard shortcut ctrl+enter

  drawer right trigger citation_click:
    media source_preview:
      selected item is state.ui.selected_citation
      inline crop
      annotation
      on click open_source

  card citation_row:
    on click citation_click
    text citation
```

Interaction behavior:

- Clicking `citation_row` opens the sources drawer using a deterministic `layout.drawer.open` action.
- Pressing `Ctrl+Enter` dispatches the composer click action in declaration order.
- Selection bindings store state under explicit keys, never implicit globals.

## Determinism and ordering

Phase 2 runtime behavior is deterministic by contract:

- Action IDs are stable for identical source.
- State transitions execute serially in sorted order: `order`, then `line`, then `column`, then `id`.
- Manifest actions and layout nodes are emitted in deterministic order.
- Missing targets and invalid actions raise explicit errors.

## Studio vs production

- Studio mode accepts missing `ui.custom_layouts` to support rapid debugging.
- Production/runtime mode enforces the capability and refuses to render unsupported layouts.
- Renderer fallback is explicit and user-visible; there are no silent failures.

## Existing template

`templates/ui/rag_shell/app.ai` now includes sidebar, drawer, and sticky composition so you can start from a working RAG-style layout shell.
