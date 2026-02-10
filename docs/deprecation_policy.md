# Deprecation Policy

Deprecations are explicit, deterministic, and time-bounded.

## Lifecycle

1. **Warn phase**: compile-time warning with migration guidance.
2. **Enforced phase**: usage becomes an error at or after the declared version.
3. **Removal phase**: feature may be removed in a major release after enforcement.

## Rule requirements

Every deprecation rule must define:

- unique rule ID
- deprecated token/API
- replacement path
- `deprecated_in` version
- `error_in` version

Rules are implemented in `src/namel3ss/lang/deprecation.py`.

## Warning behavior

- warnings are emitted in deterministic order
- warnings include replacement instructions
- warnings include the future enforcement version

## Error escalation

- escalation is version-driven and deterministic
- once current version is `>= error_in`, compilation fails for the deprecated usage

## Current capability deprecations

- `ui_theme` -> `ui.theming` (error in `2.0.0`)
- `custom_ui` -> `ui.plugins` (error in `2.0.0`)
- `custom_theme` -> `ui.theming` (error in `2.0.0`)

## Migration guidance

- apply replacements before enforcement versions
- run validation and CI after migration
- keep both compatibility and deprecation policy docs updated for every new rule
