# Stability (alpha)

namel3ss is in early alpha. We keep core behavior predictable while we iterate.

## Stable now
- CLI entrypoints: `n3 <app.ai>`, `check`, `ui`, `actions`, `studio`, `format`, `lint`.
- Core grammar: flows, records, pages, AI profiles, agents, layout primitives (section/card/row/column/divider/image).
- Expressions: decimal literals, arithmetic (+ - * /), and if/else conditionals with comparisons.
- Record creation: `create "Record" with <values> as <var>` (legacy `save Record` still supported).
- Studio API endpoints (`/api/summary`, `/api/ui`, `/api/actions`, `/api/lint`, `/api/action`, `/api/edit`).
- UI manifest shape (element types, ids, page/slug/index metadata).
- UI manifest `theme.schema_version` is `1`. Bump only on breaking manifest changes; additive fields do not bump the schema version.
- Type canon: `text`, `number`, `boolean` (and `json` if present). Legacy aliases (`string`/`int`/`bool`) are deprecated; formatter rewrites and lint errors by default.

## May change
- Experimental UI DSL details (new primitives may be added).
- Formatting details and lint rules.
- Templates and examples as we learn.
- Capsules (modules) and the built-in `n3 test` runner while the ecosystem matures.
- Package manager commands (`n3 pkg`) and `packages/` installs while the ecosystem matures.

## Breaking changes policy
- No silent breaks: breaking changes are recorded in the changelog.
- Deprecated patterns will be surfaced via lint/formatter where possible.
- File-first workflow remains: `.ai` is the source of truth; CLI commands stay stable.
- Strict types opt-in: toolchain can reject legacy type aliases with `--no-legacy-type-aliases` or `N3_NO_LEGACY_TYPE_ALIASES=1`. Default remains compatible for now; use canonical types.
- Persistence v1: opt-in via `N3_PERSIST_TARGET` (`sqlite`, `postgres`, `edge`). Legacy `N3_PERSIST=1` still enables SQLite (`.namel3ss/data.db`). Inspect via `n3 data`; reset persisted data with `n3 data reset --yes` (SQLite only). Default remains in-memory; no traces/secrets are persisted. SQLite schema version is `2` with primary-key and unique-field indexes; migrations run automatically on open. Pragmas: WAL mode + `synchronous=NORMAL`, `foreign_keys=ON`, `busy_timeout=5000` to keep writes safe while improving throughput.
