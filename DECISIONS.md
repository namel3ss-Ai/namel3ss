# Decisions Log

This file is the canonical log for language-governance decisions.
Entries are append-only and ordered by logical index.

## Entry format
- `decision_id`: deterministic sequential identifier
- `rfc_id`: RFC identifier
- `status`: accepted or rejected
- `spec_version`: target version
- `summary`: short plain-language decision
- `rationale`: why the committee decided this way

## Decisions

### D-0001
- decision_id: D-0001
- rfc_id: RFC-0000
- status: accepted
- spec_version: 1.0.0
- summary: Formalize and freeze the baseline language specification.
- rationale: A machine-verifiable baseline is required for stable tooling and deterministic upgrades.

### D-0002
- decision_id: D-0002
- rfc_id: RFC-0001
- status: accepted
- spec_version: 1.0.0
- summary: Require RFC review for grammar or semantic changes.
- rationale: Prevent untracked language drift and keep compatibility guarantees explicit.

### D-0003
- decision_id: D-0003
- rfc_id: RFC-0002
- status: accepted
- spec_version: 1.0.0
- summary: Publish governance and education baseline artifacts.
- rationale: Contributors need a clear process and learning path before broad ecosystem growth.
