# CLI: with

`n3 with` writes and renders a deterministic tool proof pack.

## What it is
- A tool gate summary for each tool call in a run.
- A stable report of allowed, blocked, and failed tool calls.

## What it includes
- Count of tool calls.
- Allowed tool summaries.
- Blocked tool summaries with reasons and capabilities.
- Error tool summaries.
- Deterministic notes (when present).

## What it does NOT include
- Tool internals or side effects.
- Inferred intent beyond trace facts.

## Artifacts
Artifacts are written under:
- `.namel3ss/tools/last.json`
- `.namel3ss/tools/last.plain`
- `.namel3ss/tools/last.with.txt`
