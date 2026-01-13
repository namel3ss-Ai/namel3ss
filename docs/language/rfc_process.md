# RFC Process

The grammar and semantics of namel3ss are frozen. Any change that affects the language contract must go through this RFC process before code changes are proposed.

## When an RFC is required
- Grammar or lexer changes (keywords, precedence, syntax acceptance).
- Semantic changes to STATIC or RUNTIME validation behavior.
- Changes to identity/trust/permissions enforcement rules.
- Modifying default state or action ID semantics.
- Removing or altering contract tests.

## What is not an RFC
- Documentation or onboarding clarifications.
- Additional warnings or improved diagnostics that do not change behavior.
- Performance optimizations that keep observable behavior stable.
- Studio/CLI UX polish that preserves parity.

## RFC expectations
- Problem statement and motivation.
- Proposed change and scope (what changes, what does not).
- Backward-compatibility impact and migration plan.
- Test updates required (contract/grammar/manifest).
- Rollout and deprecation plan if applicable.

## Review and acceptance
- RFCs must be reviewed by maintainers with language ownership.
- Approval is required before any implementation PR is opened.
- Breaking changes require documented migration notes and timelines.

## Traceability
- Link RFCs in PR descriptions that implement them.
- Do not merge code changes that alter grammar/semantics without a referenced, accepted RFC.
