# RFC-0000: Specification and Governance Foundation

- status: accepted
- target_spec_version: 1.0.0
- authors: [core]

## Motivation
The language needs a stable source of truth and a public change process.

## Proposal
Publish a versioned grammar under `spec/grammar/v1.0.0/` and require RFC approval for language-surface changes.

## Backward compatibility
No syntax changes are introduced in this RFC.

## Determinism impact
Specification files are immutable per version. Governance decisions are logged in `DECISIONS.md`.

## Test plan
Add tests for spec registry loading and governance artifact presence.
