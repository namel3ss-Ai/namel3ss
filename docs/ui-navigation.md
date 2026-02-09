# UI Navigation

`ui_navigation` adds deterministic multi-view navigation to namel3ss UIs.

## Capability

Add the capability before using navigation:

```ai
capabilities:
  ui_navigation
```

Without it, compile-time validation fails with:
`Navigation requires capability ui_navigation. Add 'ui_navigation' to the capabilities list.`

## Sidebar Navigation

Declare an app-level sidebar:

```ai
capabilities:
  ui_navigation

nav_sidebar:
  item "Chat" goes_to "Chat"
  item "Sources" goes_to "Sources"
  item "Settings" goes_to "Settings"

page "Chat":
  text is "Chat page"

page "Sources":
  text is "Sources page"

page "Settings":
  text is "Settings page"
```

Or a page-level sidebar:

```ai
capabilities:
  ui_navigation

page "Chat":
  nav_sidebar:
    item "Chat" goes_to "Chat"
    item "Sources" goes_to "Sources"
  text is "Chat page"

page "Sources":
  text is "Sources page"
```

Targets must reference existing page names.

## Navigation Actions

Buttons and list/table/card actions support:

```ai
capabilities:
  ui_navigation

page "Chat":
  button "Open settings":
    navigate_to "Settings"
  button "Back":
    go_back

page "Settings":
  text is "Settings page"
```

`navigate_to` targets are compile-time validated.

## Runtime Behavior

- Only one page renders at a time.
- URL query `?page=<slug>` stays in sync with the active page.
- Browser back/forward (`popstate`) restores the matching page.
- Sidebar active state follows the current page deterministically.

## Determinism

- Page order is source order.
- Sidebar item order is declaration order.
- Same manifest + state yields the same active page and DOM branch.
