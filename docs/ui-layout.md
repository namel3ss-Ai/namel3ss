# Layout

Layout supports two deterministic page shapes:
- Legacy stack: `page.elements` (vertical order as declared).
- Slot layout: `page.layout` with `header`, `sidebar_left`, `main`, `drawer_right`, `footer`.

For the Phase 1 custom layout grammar (`sidebar`, `drawer`, `sticky`, `scroll area`, `two_pane`, `three_pane`, and interaction hooks), see `docs/specs/layout_interaction_spec.md`.

For slot layouts:
- Evaluation order is fixed: `header` -> `sidebar_left` -> `main` -> `drawer_right` -> `footer`.
- Responsive sidebar collapse uses a fixed breakpoint at `960px`.
- Sidebar and right drawer regions scroll independently from main content.
- Empty slots are omitted from the DOM.

## Diagnostics Separation
- Mark diagnostics-only pages with `diagnostics is true`.
- Add per-page diagnostics content under `layout: diagnostics:`.
- In production mode, diagnostics pages and diagnostics blocks are omitted by default.
- In Studio mode, diagnostics are available and can be toggled with `Show Explain`.
- `n3 run --diagnostics <app.ai>` enables diagnostics rendering outside Studio for debugging.

## Conditional visibility
- Use `visible when <expr>` on pages, sections, cards, tabs, lists, and tables.
- Alias forms remain valid: `visibility is <expr>`, `when is <expr>`, `visible_when: <expr>`.
- Visibility is evaluated deterministically before rendering children.
- `list` and `table` support `empty_state: hidden` (or `empty_state: false`) to suppress empty components entirely.

## RAG Layout Pattern
- Keep `scope_selector` in `sidebar_left` to control retrieval scope.
- Render answer text in `main`, then `citations from state.<path>` and `trust_indicator from state.<path>`.
- Render `source_preview from state.<path>` in `drawer_right` so chip clicks open stable source context.
- Citation chips number deterministically in declaration/state order.

## Chat Presentation
- `chat` supports `style`, `show_avatars`, `group_messages`, `actions`, `attachments`, and `streaming`.
- Grouping is deterministic by message order and role; the first message in each sender run gets `group_start: true`.
- Message actions render in declaration order (`copy`, `expand`, `view_sources`).
- When `streaming is true`, the `thinking` indicator becomes user-visible and the active assistant message is marked streaming.
- Attachment rendering is deterministic by message order; supported types are `citation`, `file`, and `image`.

## Warnings
- `layout.flat_page_sprawl` - many top-level elements without grouping.
- `layout.data_ungrouped` - multiple data-heavy elements not inside labeled containers.
- `layout.action_heavy` - too many actions in one container.
- `layout.deep_nesting` - container depth exceeds the limit.
- `layout.grid_sprawl` - too many columns in a row.
- `layout.mixed_record_representation` - a record appears as both table and list.
- `layout.inconsistent_columns` - the same record uses multiple column sets.
- `layout.unlabeled_container` - sections, cards, tabs, drawers, or modals lack labels.
- `visibility.missing_empty_state_guard` - list/table may show empty-state copy without an explicit visibility guard.
- `diagnostics.misplaced_debug_content` - debug/diagnostics content is in product layout; move it to `layout.diagnostics` or mark it `debug_only`.

## Fix
Group related content, keep rows small, and keep record layouts consistent.

## Example
```ai
record "Order":
  id text

page "home":
  layout:
    header:
      title is "Orders"
      text is "Review incoming orders."
    sidebar_left:
      section "Queue":
        text is "Open"
    main:
      section "Open orders":
        table is "Order"
    footer:
      text is "v1"
```
