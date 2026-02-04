# Patterns

Patterns are living reference apps. There is no `reference_apps/` directory; `patterns/` is the reference app catalog.
They must remain runnable and verified on every release.

## How to propose a new pattern

1) Create a new folder under `patterns/<pattern-id>/`.
2) Include required files:
   - `app.ai`
   - `modules/` (capsules)
   - `tests/` (run `n3 test`)
   - `namel3ss.toml`
   - `namel3ss.lock.json`
   - `packages/` (empty is OK)
3) Ensure the pattern passes:
   - `n3 test`
   - `n3 verify --prod`
4) Add the entry to `patterns/index.json` with a one-line description.

## Rules

- Keep flows deterministic and offline.
- No secrets in `.ai` or docs.
- Use identity + requires for mutations and forms.
- Keep every file under 500 lines.

## PR checklist (enforced by CI)

- Pattern runs `n3 test` and `n3 verify --prod`.
- Lockfile exists; packages include licenses if present.
- One-page docs in `docs/models/` remain valid.
