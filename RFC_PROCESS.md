# RFC Process

Any change that affects grammar, semantics, determinism contracts, or compatibility policy must follow this RFC process.

## 1. Open an RFC
- Use the RFC template in `.github/ISSUE_TEMPLATE/rfc.yml`.
- Include: problem, proposal, alternatives, compatibility impact, migration plan, and test updates.
- Assign a stable RFC ID, for example `RFC-0021`.

## 2. Public discussion
- Keep the RFC open for community review.
- Capture major concerns and alternatives in the RFC thread.
- Do not merge implementation code during active unresolved discussion.

## 3. Committee review
- Language Steering Committee evaluates scope and risk.
- The review checks:
  - determinism impact
  - backward compatibility
  - operational safety
  - documentation and test completeness

## 4. Decision
- Decision options: `accepted`, `rejected`, `needs_changes`.
- Accepted RFCs are recorded in `DECISIONS.md` with:
  - RFC ID
  - status
  - target spec version
  - rationale

## 5. Implementation gate
- Implementation PRs must reference an accepted RFC ID.
- Grammar-surface changes without an accepted RFC fail governance checks.
- Contract and compatibility tests must be updated in the same PR.

## 6. Release and immutability
- Each language-spec release is versioned under `spec/grammar/vX.Y.Z/`.
- Once released, spec files for that version are immutable.
- Any follow-up change requires a new RFC and a new version.

## Non-RFC changes
The following usually do not require an RFC:
- docs clarifications
- diagnostics wording updates without behavioral changes
- internal refactors that preserve observable behavior

If there is uncertainty, open an RFC first.
