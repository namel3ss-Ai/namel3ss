# Composition rules

Namel3ss composition is deterministic and layer-scoped.

1. Theme composition:
   - App-level theme defaults are applied first.
   - Page-level theme overrides apply next.
   - Runtime theme state (when enabled) applies last.
2. Page composition:
   - Slot layout pages are evaluated in canonical slot order: `header`, `sidebar`, `main`, `footer`.
   - Retrieval explain elements are injected ahead of non-error content in the active slot.
3. Module composition:
   - Imported module exports must be explicit.
   - Flow and UI names must be unique at composition time.
   - Unsupported exported actions are dropped by export guards instead of re-ordered or rewritten.

Composition order is stable across runs, and manifests are serialized canonically.
