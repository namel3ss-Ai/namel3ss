# Templates

Templates are canonical, production primitives. They define stable program shapes that are safe to copy, extend, and audit.

## Structure

Each template lives under `templates/<name>/` and must contain:

- `README.md`
- `app.ai`

Optional:

- `fixtures/` (only deterministic, repo-safe fixtures)

## Template README

Each template README must include the following stable headings:

- Purpose
- Entry
- Contracts
- Explain
- Fixtures
- Verify

## Determinism and safety

Templates must remain deterministic and offline by default:

- No timestamps
- No randomness
- No network access
- No repo artifacts
- No host paths or secrets in outputs

## Index

`templates/index.md` lists templates in alphabetical order by folder name. Each entry includes the template name and repo-relative path. If a shortcut is listed, it is a static identifier only and must not execute the template.

Templates may be empty initially; the contract remains valid without any entries.
