# Changelog

No breaking changes without an explicit changelog entry.

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
- Full-stack UI + actions (Phase 4): Pages, actions, and runtime wiring for forms/buttons/tables.
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
