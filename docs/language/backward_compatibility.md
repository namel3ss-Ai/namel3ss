# Backward Compatibility Policy

This policy defines how the frozen namel3ss grammar and semantics may evolve. Compatibility is governed by rules, not versioned filenames.

## What counts as a breaking change
- Grammar or lexer changes (new/removed keywords, altered precedence, different parse acceptance).
- Removing syntax or altering the meaning of existing constructs.
- Changing STATIC or RUNTIME semantics (identity, permissions, state, or validation responsibilities).
- Altering action ID generation or default state behavior in a way that breaks existing manifests.

## Allowed without breaking compatibility
- Improved diagnostics or warnings that keep behavior intact.
- Additional structured warnings in STATIC mode.
- Studio and CLI UX improvements that do not change parse/build/runtime semantics.
- Performance, determinism, or tooling optimizations that preserve observable behavior.

## Process for breaking changes (if ever required)
- Publish an RFC describing the change, migration path, and risk.
- Provide deprecation warnings where possible and a documented migration window.
- Update contract docs and contract tests to reflect the new behavior, with explicit approval.

## Enforcement
- Grammar and contract tests must fail on incompatible changes.
- `docs/language/grammar_contract.md` is authoritative; updates require compatibility review.
- Removal or modification of guardrails (docs or tests) is itself a breaking change and must follow the same RFC process.
