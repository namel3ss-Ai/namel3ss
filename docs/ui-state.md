# UI State Lifecycle

`ui_state` makes UI state explicit, typed, and scoped.

## Capability

`ui_state` requires capability `ui_state`.

```ai
capabilities:
  ui_state
```

## Syntax

```ai
capabilities:
  ui_state

ui_state:
  ephemeral:
    stream_phase is text
  session:
    current_page is text
    drawer_open is boolean
  persistent:
    theme is ThemeSettings
```

Rules:

- Declare `ui_state` once at app level.
- Valid scopes: `ephemeral`, `session`, `persistent`.
- Keys are static and unique across all scopes.
- Every entry uses `key is type`.

## Semantics

- `ephemeral`: memory only, not persisted.
- `session`: restored from session storage for the current browser session.
- `persistent`: restored from local storage across sessions.

Restore order is deterministic:

1. Initialize declared defaults.
2. Apply session values.
3. Apply persistent values.

## Validation

Compiler validation enforces:

- Missing capability error for `ui_state`.
- `state.ui.*` reads must reference declared keys.
- `state.ui.*` writes must reference declared keys.

## Manifest / Studio

When declared, the manifest includes `ui_state` metadata:

- declared fields (`path`, `scope`, `type`)
- current scoped values
- value source (`default` or `restored`)

Studio state inspector renders this metadata for debugging and review.
