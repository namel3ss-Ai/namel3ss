# Ecosystem, Tutorials, and Tooling

This phase adds a deterministic ecosystem workflow for marketplace packages, guided tutorials, and local developer tooling.

## Marketplace

- Manifest files can be `manifest.yaml` or `capability.yaml`.
- Publish, search, install, approve, rate, and comments are available through `n3 marketplace`.
- Installing an item writes deterministic install metadata to `capabilities.yaml` under `marketplace_items`.

## Tutorials

- List lessons: `n3 tutorial list --json`
- Run a lesson: `n3 tutorial run basics --auto --json`
- Progress is stored in `.namel3ss/tutorial_progress.json`.
- Lesson snippets are parsed in a temporary sandbox to avoid writing app state.

## Playground

Studio now includes a Playground panel:

- `Check` validates a snippet.
- `Run` executes the first pure flow in a sandboxed worker with a timeout.

The API endpoints are:

- `POST /api/tutorials` with `action: list|run`
- `POST /api/playground` with `action: check|run`

## CLI tooling

- `n3 init <project_name>` creates a deterministic starter project.
- `n3 scaffold test <flow>` generates a Python test skeleton from flow contracts.
- `n3 package build --out dist` creates a deterministic zip archive.
- `n3 lsp stdio` starts the language server process.
- `n3 lsp check app.ai --json` returns deterministic diagnostics.
- `n3 docs --offline` prints the local docs path.
