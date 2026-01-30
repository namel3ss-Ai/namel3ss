# Templates

## Purpose
- Provide a single home for canonical templates.
- Keep structure, naming, and invariants stable.

## Scope
- This folder is documentation and source only.
- Runtime scaffolding remains in `src/namel3ss/templates/`.
- No execution tooling or auto-discovery lives here.

## Structure
Each template lives in `templates/<name>/` and must include:
- `README.md`
- `app.ai`

Optional:
- `fixtures/` (deterministic, repo-safe only)

Additional files are allowed only when deterministic and documented in the template README.

## Naming
- Use short nouns only.
- Use lowercase snake_case.
- No numbers, phases, or marketing terms.

## Template README
Each `templates/<name>/README.md` must include these headings in this order:
- Purpose
- Entry
- Contracts
- Explain
- Fixtures
- Verify

## Entry
- Entry file: `app.ai` (canonical entry extension in this repo).
- CLI entry: `n3 new <template> <project_name>` (reserved; wiring is external to this folder).

## Contracts
Every template must document deterministic invariants, including:
- No timestamps, randomness, host paths, or secrets.
- Stable ordering for lists and outputs.
- No runtime artifacts committed to the repo.
- No external dependencies or setup beyond the runtime.

## Explain
Document the explain surfaces for the template in one or two lines.

## Fixtures
If `fixtures/` exists, include only deterministic, repo-safe data.

## Verify
List deterministic checks for the template (for example, `n3 app.ai check`).
