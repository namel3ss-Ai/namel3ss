# Application UI Model

The Application UI Model is the language-level contract for how namel3ss apps describe pages, layout, components, and navigation. It is declarative, deterministic, and part of every `.ai` program.

## What the UI Model covers
- **Pages**: named screens declared with `page "name":` plus optional `purpose`, `title`, and copy.
- **Layout**: sections, cards, lists, tables, forms, and charts placed in source order. Layout is semantic, not imperative.
- **Components**: buttons, links, text, forms, tables, views, stories, charts, and media. Components bind to records, state, or actions explicitly.
- **Navigation**: named pages plus explicit links between them keep routing deterministic and reload-safe.
- **Bindings**: buttons and UI events call named flows (`calls flow "save"`). Forms and tables bind to records; displays can read from `state.<path>` or record views.

## Declaring pages
```ai
page "home":
  purpose is "Primary workspace for the app."
  title is "Orders"
  text is "Review and manage orders."
  card "Actions":
    button "Refresh":
      calls flow "refresh_orders"
  card "Orders":
    table is "Order"
```
- Pages are first-class; each declaration becomes a page in the manifest with a stable id based on its name.
- Content order is preserved as written; deterministic ordering is required for stable UI manifests.

## Layout and components
- **Sections/Cards**: group content; keep semantic intent (e.g., `card "Summary"`).
- **Forms/Tables/Views**: bind to records; schema comes from record declarations.
- **Buttons**: trigger flows via `calls flow "name"`; no implicit actions exist.
- **Links**: navigate to named pages with `link "Label" to page "PageName"`.
- **Stories/Text/Media**: explanatory content that renders deterministically.
- **Charts**: render read-only data from records or state; inputs must be explicit.
- All components are declared inline under their parent page or container; no hidden defaults.

## Navigation
- Multiple `page` blocks define navigation targets.
- The runtime loads the first declared page as the initial route; subsequent pages appear in source order.
- Links must reference pages by name; no generated ids.
- URL handling stores the current page slug under `?page=` to keep reloads stable.

Example:
```ai
page "home":
  title is "Home"
  link "Settings" to page "Settings"

page "Settings":
  title is "Settings"
  link "Back" to page "home"
```

## Manifest and determinism
- The UI manifest emitted at `/api/ui` lists pages and actions in source order using canonical JSON serialization.
- Page, action, and component identifiers derive from declarations; there are no random ids or timestamps.
- State bindings resolve to explicit state paths; forms and tables bind to declared records.
- Adding pages or components preserves ordering; removing or reordering declarations updates the manifest deterministically.

## How it connects to state and actions
- Flows update state and records; pages read from state or records explicitly.
- Action results are reflected in `/api/state` and are rendered by bound components (tables, views, charts, messages).
- UI declarations do not perform logic; all logic lives in flows.

## Related references
- Browser Protocol: `/api/ui`, `/api/state`, `/api/action`, `/api/health`.
- UI DSL reference: `docs/ui-dsl.md`.
- Runtime guide: `docs/runtime.md`.
