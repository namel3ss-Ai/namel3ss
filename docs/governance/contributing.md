# Governance Contribution Rules

## Source of Truth
Contributors **must** treat `docs/spec/*` as normative for `namel3ss-spec@1`.

## Required Change Discipline
When touching grammar, runtime semantics, or contracts:
1. Update spec/governance docs as needed.
2. Keep changes additive unless explicitly marked breaking.
3. Run governance checks locally.
4. Include tests that prove deterministic behavior.

## Breaking Change Procedure
- Add explicit acknowledgment (`BREAKING_CHANGE_ACK=1` or CI label override).
- Update compatibility and migration notes.
- Update frozen snapshots where required.

## CI Governance Gates
PRs **must** pass:
- spec diff check
- grammar snapshot check
- contract compatibility check
