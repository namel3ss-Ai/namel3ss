# UI See

Explainable ui shows what the user sees and what they do not see.
Output is deterministic and based only on the ui manifest and action guards.
It never includes CSS, visual layout guesses, or AI reasoning.

## Quick use
Render the ui manifest, then ask what the user sees:
```bash
n3 ui app.ai
n3 see
```

## What it includes
- Page list and element summary.
- Elements per page with labels and bindings (forms, tables, lists, charts, chat, overlays, tabs).
- Actions and whether they are available (flow calls and UI-only open/close/selection).
- Requires guards when present.
- Pack origin metadata when elements come from `ui_pack` expansion.

## Bounds
- Output is deterministic and bounded.
- Long lists are truncated with an explicit marker (e.g., `... (+N more)`).

## What it does not include
- CSS or layout details.
- Guessed visibility rules.
- Hidden elements without explicit rules.
- Runtime-only data (record rows, chart series, chat payloads, or selection state).

## Artifacts
After a run, the runtime saves:
- `.namel3ss/ui/last.json`
- `.namel3ss/ui/last.plain`

The `n3 see` command writes:
- `.namel3ss/ui/last.see.txt`
