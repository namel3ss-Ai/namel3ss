# Application Runtime Contract

Every valid `.ai` program is an application. The runtime reads declarations and produces a deterministic app: UI manifest, flows, tools, memory, and traces.

## What this contract covers
- `.ai` files are self-contained applications; no extra framework or scaffolding layer is required to run them.
- `n3 run` / `n3 dev` / `n3 preview` render the UI manifest in the browser and wire actions to flows using the same manifest that Studio inspects.
- `n3 run` defaults to production UI mode; `n3 run studio` (or `--studio`) enables Studio instrumentation in the rendered manifest.
- `n3 start` serves the built manifest; `n3 app.ai` without a subcommand executes the default application flow.
- The runtime surface is identical in CLI and Studio; Studio is an inspector/debugger only.

## Browser as renderer
- Browser sessions receive the generated UI manifest; actions call flows by id and sync state after each call.
- The manifest is deterministic: ordering, ids, and fields match `n3 ui`.
- State sync is explicit: flows mutate state, UI re-renders on state changes, and there is no hidden client logic.

## Studio as inspector
- `n3 run studio app.ai` enables Studio-oriented manifest content while keeping runtime behavior unchanged.
- `n3 app.ai studio` opens the dedicated Studio inspector for the same program.
- Studio adds "Why?" explanations and trace inspection; it does not change flow logic or required steps to run the app.
- Apps run without Studio; Studio is optional and read-only for rendering.

## Debug-only UI metadata
- UI declarations may include optional `debug_only` metadata.
- `debug_only` accepts only boolean literals (`true` or `false`).
- In production mode, `debug_only: true` pages and elements are omitted from the rendered manifest.
- In Studio mode, those pages and elements are rendered normally.

## Minimal example
```ai
spec is "1.0"

record "Note":
  fields:
    body is text must be present

flow "save_note":
  set state.note with:
    body is "Hello World"
  save "Note" with state.note as saved
  return saved

page "home":
  title is "Notes"
  button "Save sample":
    calls flow "save_note"
```

- `n3 run` renders the page in production mode and calls `save_note` when the button runs.
- `n3 run studio` renders the same app with Studio instrumentation enabled.
- `n3 ui` prints the manifest used by the runtime contract.
- `n3 app.ai studio` inspects the same app with traces and "Why?" panels.
