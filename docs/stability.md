# Stability (alpha)

namel3ss is in early alpha. We keep core behavior predictable while we iterate.

## Stable now
- CLI entrypoints: `n3 <app.ai>`, `check`, `ui`, `actions`, `studio`, `format`, `lint`.
- Core grammar: flows, records, pages, AI profiles, agents, layout primitives (section/card/row/column/divider/image).
- Studio API endpoints (`/api/summary`, `/api/ui`, `/api/actions`, `/api/lint`, `/api/action`, `/api/edit`).
- UI manifest shape (element types, ids, page/slug/index metadata).
- UI manifest `theme.schema_version` is `1`. Bump only on breaking manifest changes; additive fields do not bump the schema version.
- Type canon: `text`, `number`, `boolean` (and `json` if present). Legacy aliases (`string`/`int`/`bool`) are deprecated; formatter rewrites and lint errors by default.

## May change
- Experimental UI DSL details (new primitives may be added).
- Formatting details and lint rules.
- Templates and examples as we learn.

## Breaking changes policy
- No silent breaks: breaking changes are recorded in the changelog.
- Deprecated patterns will be surfaced via lint/formatter where possible.
- File-first workflow remains: `.ai` is the source of truth; CLI commands stay stable.
- Strict types opt-in: toolchain can reject legacy type aliases with `--no-legacy-type-aliases` or `N3_NO_LEGACY_TYPE_ALIASES=1`. Default remains compatible for now; use canonical types.
