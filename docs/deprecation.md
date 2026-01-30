# Deprecation

Deprecation is a controlled compatibility mechanism. Behavior stays stable until an explicit migration path exists.

## Policy
- Deprecations must be announced with deterministic warnings.
- Warnings appear in CLI output and explain surfaces where applicable.
- Deprecated behavior remains supported until a migration plan is available.

## Removal
- Removal requires an explicit migration tool and opt-in.
- Removal without a migration path is not permitted.

## Records
- Deprecation notices are documented in contract docs and changelog notes.
- Warnings and notices are stable, ordered, and redacted.
