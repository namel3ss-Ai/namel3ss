# RAG UI Interaction Model

This guide documents the default RAG chat interaction contract used by manual UI layouts and `rag_ui` expansion.

## Streaming behavior

- Assistant tokens stream into one message bubble in arrival order.
- Before the first token, the bubble shows a subtle thinking indicator.
- Citation chips under a streaming answer are deferred until the stream completes.

Determinism:

- Token append order follows token array order.
- Stream completion state is explicit (`thinking` -> `streaming` -> `complete`).
- The same message payload produces the same final DOM.

## Evidence-first citations

- Citation chips render directly under assistant messages when citations exist.
- Clicking a chip opens the citation drawer, selects the citation, and scrolls to the selected source item.
- Source list interactions route to preview mode for the selected citation.

## Drawer model

The citation drawer provides three deterministic tabs:

- `Sources`: source list and selection
- `Preview`: page/snippet preview with highlight
- `Explain`: plain-language rationale

Behavior:

- Opening the drawer from a chip lands on `Sources` with selection applied.
- Choosing a source from the list switches to `Preview`.
- Drawer focus trapping is active on mobile-width viewports.

## Empty/loading/error states

- No sources: onboarding panel with `Upload document` primary action.
- Retrieving: inline status `Searching sources...`.
- Generating: streaming message with thinking indicator.
- Errors: friendly user copy in chat surfaces; no stack traces in production UI.

## Confidence badge

The confidence indicator is intentionally coarse and trust-forward:

- `Grounded`
- `Partial`
- `No sources`

Rules:

- Unknown confidence is hidden.
- Mapping is deterministic from manifest/state values.

## Keyboard and accessibility

- `Enter` sends message.
- `Shift+Enter` inserts newline in composer.
- Focus returns to composer after send.
- Focus-visible outlines remain visible on interactive controls.

## Files

- `src/namel3ss/studio/web/ui_renderer_chat.js`
- `src/namel3ss/studio/web/ui_renderer_rag.js`
- `src/namel3ss/studio/web/ui_renderer.js`
- `src/namel3ss/studio/web/styles/chat.css`
- `src/namel3ss/studio/web/styles/drawer.css`
- `src/namel3ss/studio/web/styles/empty_states.css`
