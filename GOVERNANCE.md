# Governance

Namel3ss is governed as a stable language and runtime platform.
This document defines who can change what, how decisions are made, and how we preserve compatibility.

## Scope

Governance covers:

- Public language and manifest contracts.
- Determinism guarantees and contract tests.
- Backward compatibility and deprecation policy.
- Release readiness and long-term support guarantees.

Governance does not cover private maintainer logistics or commercial terms.

## Language Steering Committee

The **Language Steering Committee** (LSC) is the decision authority for public contracts.

### Maintainer roles

- **Chair**: owns agenda, final tie-break, and release sign-off.
- **Secretary**: records decisions in `DECISIONS.md` and keeps policy docs current.
- **Maintainer reviewers**: review RFCs, approve merges, and enforce compatibility policy.
- **Security maintainer**: owns coordinated disclosure process and security exceptions.

### Membership and terms

- Core maintainers are listed in `CONTRIBUTORS.md`.
- Community seats are elected every 12 months.
- Membership changes are recorded in `DECISIONS.md`.

## Voting model

- Quorum: at least 3 LSC reviewers, including 1 core maintainer.
- Decision rule: simple majority of cast votes.
- Tie-break: Chair decision.
- Conflicts of interest: affected reviewers must abstain.

## Language change policy

- Grammar, runtime contracts, plugin API, and CLI contract changes require an RFC.
- RFC process is defined in `RFC_PROCESS.md`.
- Approved RFCs must include migration notes and tests before merge.
- Public specs in `docs/spec/` are immutable per released version.
- Breaking changes are only allowed in major version bumps and must comply with `docs/compatibility_policy.md`.

## Public API ownership

- Public API declarations are owned by the LSC and encoded in `src/namel3ss/lang/public_api.py`.
- Internal module boundaries are encoded in `src/namel3ss/lang/internal_api.py`.
- Deprecation timelines are encoded in `src/namel3ss/lang/deprecation.py` and documented in `docs/deprecation_policy.md`.

## Review and merge rules

- Every production change requires at least one maintainer review.
- Changes to grammar, contracts, governance, or security require two maintainer reviews.
- CI and deterministic checks must pass before merge.
- No direct pushes to protected release branches.

## Release governance

- Releases follow semantic versioning.
- `VERSION`, `CHANGELOG.md`, release checklist, and release workflow must align.
- Release artifacts must be reproducible from the same commit and inputs.
- LSC publishes GA and LTS status in `docs/ga_release.md`.

## Security governance

- Security policy is defined in `SECURITY.md`.
- Vulnerabilities are handled via coordinated disclosure.
- Emergency fixes may bypass normal cadence but still require post-incident documentation in `DECISIONS.md`.

## Amendment process

- Changes to this file require an RFC and LSC approval.
- Every amendment must include:
  - reason for change
  - compatibility impact
  - enforcement plan (code, tests, or CI)

## Decision log

- `DECISIONS.md` is the authoritative record for accepted governance decisions.
- Entries are append-only and date-ordered.
