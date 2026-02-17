# Changelog

No breaking changes without an explicit changelog entry.

## v0.1.0a23
### Added
- None.

### Changed
- No grammar/runtime changes.

### Fixed
- None.

### Deprecated
- None.

### Removed
- None.

## v0.1.0a15
### Added
- Integration tests for combined UI features (layout, conditional rendering, RAG, diagnostics, uploads, plugins, theming).
- Headless upload action coverage through `/api/v1/actions/<id>` end-to-end tests.
- Deterministic HTTP caching coverage for versioned headless API and plugin assets.

### Changed
- Internal headless server modules and handler names use descriptive, professional naming (public `/api/v1/*` paths unchanged).
- Diagnostics panel styling now follows theme tokens (`--n3-secondary-color`, `--n3-background-color`, border-radius token).
- Studio/runtime UI renderer now loads plugin JS/CSS assets declared in `manifest.ui.plugins` deterministically and exposes custom-component mount metadata.
- Baseline manifest guardrails updated for diagnostics warnings emitted by legacy debug-oriented chat subcomponents.

### Fixed
- Versioned headless UI endpoint now emits stable `ETag` and cache headers and correctly returns `304 Not Modified` on matching `If-None-Match`.
- Plugin asset endpoints now emit immutable cache headers and `ETag`, with `304 Not Modified` behavior for conditional requests.
- Custom UI integration gap where plugin assets were declared but not loaded by renderer.

### Deprecated
- Legacy debug-oriented chat subcomponents (`thinking`, legacy `citations`, `memory`) continue to work but now trigger diagnostics placement warnings in product layouts.

### Removed
- None.

## v0.1.0a14
### Added

### Changed

### Fixed

### Deprecated

### Removed

## v0.1.0a13
### Added
- Docker Compose improvements: configurable port, user mapping, and CI docker-build job.
- Added `.env.example` with configuration options.
- Added sample `app/app.ai` for Docker.
- Added `data/` directory for runtime artifacts.

### Changed
- Simplified README Docker section with `docker compose` instructions.
- No grammar/runtime changes.

### Fixed

### Deprecated

### Removed

## v0.1.0a10
### Added

### Changed

### Fixed

### Deprecated

### Removed

## v0.1.0a7
### Changed
- Release metadata version bump to 0.1.0a7 (no runtime changes).

## v0.1.0a6
### Added
- Package manifest `namel3ss.toml` and lockfile `namel3ss.lock.json`.
- GitHub-backed package installs into `packages/` with checksum and license verification.
- `n3 pkg` commands: add/install/plan/tree/why/verify/licenses (+ `--json`).
- Packages docs and demo template (`docs/packages.md`, `src/namel3ss/templates/demo/`).
- Python tool venv support with per-app `.venv`, dependency detection, and `n3 deps` commands.
- Tool traces now include python env metadata and dependency source.
- Studio Tool Wizard for generating python tool skeletons.
- Built-in python tool packs (http, datetime, text, file, math) with no extra deps.
- `n3 doctor` now checks python tool declarations, deps, venv, and lockfile status.
- Python tool subprocess protocol v1 documentation.

### Changed
- Module resolution now checks `packages/<name>/` after `modules/<name>/`.
- Breaking change: removed the old technical tool syntax in favor of English-first tool blocks and calls.

Before:
```ai
tool "greeter":
  kind is "python"
  entry is "tools.sample_tool:greet"
  input_schema is json
  output_schema is json

flow "hello":
  let result is call tool "greeter" with input: input
```

After:
```ai
tool "greet someone":
  implemented using python

  input:
    name is text

  output:
    message is text

flow "hello":
  let result is greet someone:
    name is "Ada"
```

### Fixed

### Deprecated

### Removed

## v0.1.0a5
### Added
- Capsules module system with `modules/<name>/capsule.ai`, explicit exports, and `use "<module>" as <alias>` imports.
- Deterministic module loading with cycle detection.
- CLI: `n3 <app.ai> graph` and `n3 <app.ai> exports` (plus `--json`).
- Built-in test runner: `n3 test` with `tests/*_test.ai`.
- Docs and example project for modules/tests.

### Changed
- Form/state record paths now namespace qualified record names (modules use `state.<module>.<record>`).

### Fixed

### Deprecated

### Removed

## v0.1.0a4
### Added
- Decimal literals and arithmetic (+ - * /) with deterministic evaluation.
- If/else conditionals with `is not`, `is at least`, `is at most` comparisons.
- Canonical record creation: `create "Record" with <values> as <var>`.
- New docs for expressions/conditionals (see `docs/expressions-and-conditionals.md`).

### Changed
- Numeric engine values use Decimal internally; JSON output preserves decimals without rounding.
- Lint warns on legacy `save Record` usage (still supported).

### Fixed

### Deprecated
- Legacy `save Record` (warning only in v0.1.x; use `create` instead).

### Removed

## v0.1.0a1
### Added
- PyPI metadata polish (URLs, authors, license), no functional changes.

### Changed
- Stability: core CLI entrypoints and manifest shape stay stable; breaking changes are documented.

### Fixed

### Deprecated

### Removed

## v0.1.0-alpha

### Added
- Language core (Phases 1–3): Stable keywords, parser/AST/IR contracts, deterministic defaults.
- Full-stack UI + actions (Phase 4): Pages, actions, and engine wiring for forms/buttons/tables.
- AI + memory + tools (Phase 5): AI declarations with memory profiles and tool exposure.
- Multi-agent workflows (Phase 6): Agent declarations plus sequential/parallel agent execution.
- CLI, formatter, linter (Phase 7): File-first CLI, formatting rules, linting for grammar/safety.
- Studio (viewer → interactor → safe edits) (Phase 8): Manifest viewer, action runner, and guarded edits.
- Templates & scaffolding (Phase 10): `n3 new` with starter and demo templates.

### Changed

### Fixed

### Deprecated

### Removed
- Added canonical type enforcement: aliases (string/int/bool) are deprecated; formatter rewrites them and lint errors by default. Use text/number/boolean (json if applicable).
