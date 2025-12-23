# Changelog

No breaking changes without an explicit changelog entry.

## v0.1.0a6
### Added
- Package manifest `namel3ss.toml` and lockfile `namel3ss.lock.json`.
- GitHub-backed package installs into `packages/` with checksum and license verification.
- `n3 pkg` commands: add/install/plan/tree/why/verify/licenses (+ `--json`).
- Packages docs and demo example (`docs/packages.md`, `examples/demo_packages/`).

### Changed
- Module resolution now checks `packages/<name>/` after `modules/<name>/`.

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
- New examples and docs for expressions/conditionals (see `examples/demo_order_totals.ai`, `docs/expressions-and-conditionals.md`).

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
- Templates & scaffolding (Phase 10): `n3 new` with CRUD, AI assistant, and multi-agent templates.

### Changed

### Fixed

### Deprecated

### Removed
- Added canonical type enforcement: aliases (string/int/bool) are deprecated; formatter rewrites them and lint errors by default. Use text/number/boolean (json if applicable).
