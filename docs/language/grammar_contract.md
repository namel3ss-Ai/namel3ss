# namel3ss Grammar Contract

> This document defines the frozen grammar and semantics of namel3ss. Changes require explicit compatibility review.

## Scope
- The rules below are authoritative for all parsers, builders, and tooling.
- Reserved words, identifiers, expressions, and match blocks follow a single canonical form.
- Static vs runtime responsibilities are fixed; any change must go through compatibility review.

## Identifiers (bare or quoted, everywhere)
- Names may be bare (`[A-Za-z_][A-Za-z0-9_]*`) or quoted strings.
- Reserved words must be quoted when used as identifiers.
- Dot-qualified references use the same rule for every segment; keywords are allowed when quoted.

## Expressions (existence checked only at runtime)
- Expression grammar is stable; parsing never validates runtime existence of state, identity, records, or flows.
- `state.*` paths and attribute access are accepted syntactically; missing data is a runtime or build-time semantic concern.
- Static validation may warn about undeclared paths but cannot reject syntactically valid expressions.

## Match grammar (single canonical form)
- `match <expression>:` must include a `with:` block containing `when` arms; `otherwise` is optional.
- No alternate syntaxes are permitted; absence of `with:` is a parse error.
- `when` arms use the same expression grammar; ordering and exhaustiveness are runtime semantics.

## Validation phases (parse / build / runtime)
- **Parse**: Enforces grammar and token rules only; succeeds if the source conforms to this contract.
- **Build (STATIC)**: Performs structural validation, shape checks, and emits warnings for runtime-only requirements; must not require environment, identity, secrets, or data presence.
- **Runtime (RUNTIME)**: Enforces identity, permissions, trust, capability checks, and data existence; failures here are errors, not warnings.

## Change control
- Grammar or semantic changes are breaking and require an explicit compatibility review and RFC.
- The `docs/grammar/current.md` file is a historical snapshot and not a contract.
- Contract tests (`tests/parser/test_grammar_current.py` and related grammar checks) must stay green to ship.
