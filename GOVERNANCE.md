# Governance

This repository uses a public, deterministic language-governance model.

## Scope
- Language grammar and semantics
- Determinism guarantees and contract tests
- Backward compatibility policy
- Release-ready language changes

## Language Steering Committee
The Language Steering Committee (LSC) governs language-level decisions.

### Roles
- Chair: runs meetings and sets agendas.
- Secretary: records decisions and keeps `DECISIONS.md` current.
- Reviewers: evaluate RFCs and vote.

### Membership and terms
- Core maintainers hold permanent seats.
- Community seats are elected every 12 months.
- Membership and current term windows are published in this file.

## Current committee
- Chair: Core Maintainer A
- Secretary: Core Maintainer B
- Reviewer: Core Maintainer C
- Community Reviewer: Community Seat 1
- Community Reviewer: Community Seat 2

## Voting model
- Quorum: at least 3 reviewers including at least 1 core maintainer.
- Decision threshold: simple majority of cast votes.
- Tie-break: Chair casts the tie-break vote.
- Conflict-of-interest: affected members must abstain.

## Language change policy
- Grammar or semantic changes must go through `RFC_PROCESS.md`.
- Approved RFCs must be logged in `DECISIONS.md` before merge.
- Published spec versions are immutable.
- Breaking changes require migration notes and rollout windows.

## Release mapping
- Spec version updates are tracked under `spec/grammar/`.
- Reference implementation remains the compiler/runtime in this repository.
- Contract tests must pass for accepted RFCs to be considered complete.

## Meeting cadence
- Regular governance review every two weeks.
- Emergency meeting allowed for severe safety/security issues.
- Notes are appended to `DECISIONS.md` in deterministic chronological order.

## Amendment process
- Changes to governance itself require an RFC and LSC majority vote.
- Amendments are versioned and logged in `DECISIONS.md`.
